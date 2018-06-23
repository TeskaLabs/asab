import abc
import logging
import asyncio

#

L = logging.getLogger(__name__)

#

class StateABC(abc.ABC):

	Tasks = []

	def __init__(self, server):
		# Used as cache of current term over server.PersistentState['currentTerm']
		self.CurrentTerm = server.PersistentState['currentTerm']
		L.warn("Entering {} state from {} in term {}".format(self, server.State, self.CurrentTerm))

		# Cancel all currently active tasks
		for t in self.Tasks:
			if not t.done():
				t.cancel()

		server.RPC.PubSub.subscribe("Application.tick!", self._on_tick)


	def _on_tick(self, event_name):
		# Remove completed tasks ...
		for i in range(len(self.Tasks)-1, -1, -1):
			t = self.Tasks[i]
			if t.done():
				del self.Tasks[i]
				try:
					t.result()
				except asyncio.CancelledError:
					pass
				except Exception as e:
					L.exception("Error during RPC task", e)


	async def finalize(self, app):
		# Cancel all currently active tasks
		for t in self.Tasks:
			if not t.done():
				t.cancel()

		self._on_tick("simulated!")


	def on_heartbeat_timeout(self, server):
		L.warn("Heartbeat ignored in {} state")


	def __str__(self):
		return self.Name

#

class FollowerState(StateABC):

	Name = "Follower"

	def __init__(self, server):
		super().__init__(server)
		server.ElectionTimer.restart(server.get_election_timeout())
		server.HeartBeatTimer.stop()

#

class CandidateState(StateABC):

	Name = "Candidate"

	def __init__(self, server):
		# Starting elections
		server.PersistentState['currentTerm'] += 1
		super().__init__(server)
		server.ElectionTimer.restart(server.get_election_timeout())

		# Synchronize heartbeating with the election
		server.HeartBeatTimer.restart(server.HeartBeatTimeout)

		# Reset voting structure
		for peer in server.Peers:
			if peer.Address is not None:
				peer.VoteGranted = False
				t = asyncio.ensure_future(self.request_vote(server, peer), loop=server.Loop)
				self.Tasks.append(t)
			else:
				peer.VoteGranted = True

		server.LeaderAddress = None

		
		#TODO: Maybe call soon server.evalute_election()
		# Can candidate goes immediatelly into a leader state?


	def on_heartbeat_timeout(self, server):
		# Send RequestVote RCP to all peers but myself
		for peer in server.Peers:
			if peer.Address is not None:
				t = asyncio.ensure_future(self.request_vote(server, peer), loop=server.Loop)
				self.Tasks.append(t)


	async def request_vote(self, server, peer):
		start_timestamp = server.Loop.time()
		try:
			response = await server.RPC.acall(peer.Address, "RequestVote",{
				"term": self.CurrentTerm,
				"candidateId": server.Id,
				"lastLogIndex": 1,
				"lastLogTerm": 1,
				},
				timeout=server.HeartBeatTimeout*0.9
			)
		except asyncio.TimeoutError:
			# No reply from a peer server
			peer.Online = False
			return

		peer.Online = True
		term = response['term']
		voteGranted = response['voteGranted']
		serverId = response['serverId']

		if (term < self.CurrentTerm):
			return
		elif (term > self.CurrentTerm):
			L.warning("Received RequestVote result for term {} higher than current term {}".format(term, self.CurrentTerm))
			return

		if peer.Id == '?':
			L.warn("Peer at '{}' is now known as '{}'".format(peer.Address, serverId))
			peer.Id = serverId
		elif peer.Id != serverId:
			L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer.Address))

		if voteGranted:
			if not peer.VoteGranted:
				peer.VoteGranted = True
				server.evalute_election()
			else:
				L.warn("Peer '{}'/'{}' already voted".format(peer.Address, serverId))

		peer.RPCdue = server.Loop.time() - start_timestamp

#

class LeaderState(StateABC):

	Name = "Leader"

	def __init__(self, server):
		super().__init__(server)
		server.ElectionTimer.stop()
		server.HeartBeatTimer.restart(server.HeartBeatTimeout)

		server.LeaderAddress = None

		for peer in server.Peers:
			peer.nextIndex = server.Log.Index + 1
			peer.matchIndex = 0

		self.send_heartbeat(server)


	def on_heartbeat_timeout(self, server):
		self.send_heartbeat(server)


	def send_heartbeat(self, server):
		for peer in server.Peers:
			if peer.Address is not None:
				t = asyncio.ensure_future(self.append_entries(peer, server), loop=server.Loop)
				self.Tasks.append(t)


	async def append_entries(self, peer, server):

		#TODO: Ensure that only single append_entries per peer is running

		start_timestamp = server.Loop.time()

		prevLogTerm = None
		prevLogIndex = None

		if server.Log.Index >= peer.nextIndex:
			prevLogTerm, prevLogIndex, le = server.Log.get(peer.nextIndex)
			entries = [le]

		else:
			prevLogTerm, prevLogIndex, _ = server.Log.get_last()
			entries = []

		try:
			response = await server.RPC.acall(peer.Address, "AppendEntries",{
					"term": self.CurrentTerm,
					"leaderId": server.Id,
					"prevLogTerm": prevLogTerm,
					"prevLogIndex": prevLogIndex,
					"entries": entries,
					"leaderCommitIndex": server.VolatileState['commitIndex'],
				},
				timeout=server.HeartBeatTimeout*0.9
			)

		except asyncio.TimeoutError:
			# No reply from a peer server
			#TODO: A good opportunity to kick a unreachable peer from a cluster
			if peer.Online != False:
				L.warn("Peer '{}' is offine".format(peer.Address))
				peer.Online = False
			return

		if peer.Online != True:
			L.warn("Peer '{}' came online".format(peer.Address))
			peer.Online = True

		peer.RPCdue = server.Loop.time() - start_timestamp

		serverId = response['serverId']
		if peer.Id == '?':
			L.warn("Peer at '{}' is now known as '{}'".format(peer.Address, serverId))
			peer.Id = serverId
		elif peer.Id != serverId:
			L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer.Address))

		success = response.get('success', False)
		if success:
			if len(entries) > 0:
				peer.nextIndex += len(entries) # This is likely not correct
			peer.matchIndex = response.get('matchIndex')
		else:
			L.warn("Peer '{}' reported unsuccessful AppendEntries".format(peer.Id))
			if peer.nextIndex > 1:
				peer.nextIndex -= 1
