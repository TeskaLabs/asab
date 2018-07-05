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


	def __str__(self):
		return self.Name

#

class FollowerState(StateABC):

	Name = "Follower"

	def __init__(self, server):
		super().__init__(server)
		server.ElectionTimer.restart(server.get_election_timeout())

#

class CandidateState(StateABC):

	Name = "Candidate"

	def __init__(self, server):
		# Vote for myself
		server.PersistentState['currentTerm'] += 1
		server.PersistentState['votedFor'] = server.Id

		super().__init__(server)
		server.ElectionTimer.restart(server.get_election_timeout())
		server.LeaderAddress = None

		lastLogTerm, lastLogIndex, _ = server.Log.get_last()

		for peer in server.Peers:
			t = asyncio.ensure_future(self._voting_loop(server, peer, lastLogTerm, lastLogIndex), loop=server.Loop)
			self.Tasks.append(t)


	async def _voting_loop(self, server, peer, lastLogTerm, lastLogIndex):

		peer.VoteGranted = False

		# Ensure that we have a fresh IP address of the peer
		peer.resolve(server.RPC)

		while True:
			start_timestamp = server.Loop.time()

			try:
				response = await server.RPC.acall(peer.Address, "RequestVote", {
					"term": self.CurrentTerm,
					"candidateId": server.Id,
					"lastLogIndex": lastLogIndex,
					"lastLogTerm": lastLogTerm,
					},
					timeout=server.HeartBeatTimeout*0.9
				)

			except asyncio.TimeoutError:
				# No reply from a peer server
				peer.Online = False
				
				dt = server.HeartBeatTimeout - (server.Loop.time() - start_timestamp)
				if dt > 0:
					await asyncio.sleep(dt)

				continue

			end_timestamp = server.Loop.time()
			peer.Online = True
			peer.RPCdue = end_timestamp - start_timestamp

			term = response['term']
			voteGranted = response['voteGranted']
			serverId = response['serverId']

			if peer.Id == '?':
				L.warn("Peer at '{}' is now known as '{}'".format(peer.Address, serverId))
				peer.Id = serverId
				if peer.Id == server.Id:
					peer.Me = True

			elif peer.Id != serverId:
				L.warn("Server id changed from '{}' to '{}' at '{}' (ignored)".format(peer.Id, serverId, peer.Address))

			if term > self.CurrentTerm:
				L.warning("Received RequestVote result for term {} higher than current term {}".format(term, self.CurrentTerm))

			elif term == self.CurrentTerm:
				if voteGranted and not peer.VoteGranted:
					peer.VoteGranted = True
					done = server.evalute_election()
					if done or peer.is_me():
						return

			# Find a time interval for heartbeat/sleep
			dt = server.HeartBeatTimeout - (end_timestamp - start_timestamp)
			if dt > 0:
				await asyncio.sleep(dt)


#

class LeaderState(StateABC):

	Name = "Leader"

	def __init__(self, server):
		super().__init__(server)
		server.ElectionTimer.stop()

		server.LeaderAddress = None

		for peer in server.Peers:
			self.lead_peer(server, peer)


	def lead_peer(self, server, peer):
		'''
		Start leader coroutine (_peer_server_loop) for a given peer.
		'''
		peer.nextIndex = server.Log.Index + 1
		peer.matchIndex = 0
		peer.logReadyEvent = asyncio.Event(loop=server.Loop)
		peer.logReadyEvent.clear()

		if not peer.is_me():
			t = asyncio.ensure_future(self._peer_server_loop(server, peer))
			self.Tasks.append(t)


	def append_command(self, server, command):
		log_index = server.Log.append(self.CurrentTerm, command)
		for peer in server.Peers:
			peer.logReadyEvent.set()
		self._adjust_commit_index(server)
		return log_index


	async def _peer_server_loop(self, server, peer):
		while True:
			now = server.Loop.time()

			await self._append_entries(peer, server)

			#TODO: Clear only if there are no event to be send
			peer.logReadyEvent.clear()

			# Find a time interval for heartbeat/sleep
			dt = server.HeartBeatTimeout - (server.Loop.time() - now)
			if dt > 0:
				try:
					await asyncio.wait_for(peer.logReadyEvent.wait(),dt)
				except asyncio.TimeoutError:
					pass


	async def _append_entries(self, peer, server):

		#TODO: Ensure that only single append_entries per peer is running

		start_timestamp = server.Loop.time()

		prevLogTerm = None
		prevLogIndex = None
		entries = []

		# Find entries to be pushed to a peer
		d = server.Log.Index - peer.nextIndex
		if peer.Online and d >= 0:
			i = server.Log.slice(peer.nextIndex - 1, d+2)
			prevLogTerm, prevLogIndex, _ = next(i)				

			while True:
				try:
					_t , _i, e = next(i)
				except StopIteration:
					break
				assert(e is not None)
				entries.append(e)

				#TODO: Limit size of sent entries

		else:
			# No new entry to be sent
			prevLogTerm, prevLogIndex, _ = server.Log.get(peer.nextIndex-1)
			assert(peer.nextIndex-1 == prevLogIndex)


		try:
			response = await server.RPC.acall(peer.Address, "AppendEntries",{
					"term": self.CurrentTerm,
					"leaderId": server.Id,
					"prevLogTerm": prevLogTerm,
					"prevLogIndex": prevLogIndex,
					"entries": entries,
					"leaderCommit": server.VolatileState['commitIndex'],
				},
				timeout=server.HeartBeatTimeout*0.9
			)

		except asyncio.TimeoutError:
			# No reply from a peer server
			# A good opportunity to kick a unreachable peer from a cluster
			if peer.Online != False:
				L.warn("Peer '{}' is offine".format(peer.Address))
				peer.Online = False
				peer.resolve(server.RPC) # Try to obtain the IP again, maybe it changed in meanwhile
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
			peer.Id = serverId

		success = response.get('success', False)
		if success:
			if len(entries) > 0:
				peer.nextIndex += len(entries) # This is likely not correct
			peer.matchIndex = response.get('matchIndex')
			self._adjust_commit_index(server)

		else:
			L.warn("Peer '{}' reported unsuccessful AppendEntries".format(peer.Id))
			if peer.nextIndex > 1:
				peer.nextIndex -= 1


	def _adjust_commit_index(self, server):
		'''
		If there exists an N such that N > commitIndex,
		a majority of matchIndex[i] ≥ N,
		and log[N].term == currentTerm
		set commitIndex = N
		'''

		commitIndexChanged = False
		
		for N in range(server.Log.Index, server.VolatileState['commitIndex'], -1):

			count = 0
			for peer in server.Peers:
				if peer.is_me():
					# This is me, a leader
					if server.Log.Index >= N:
						count += 1
				else:
					# This is a peer / follower
					if peer.matchIndex >= N:
						count += 1

			# Do we have a majority for a given N?
			if count <= (len(server.Peers) / 2):
				continue

			e_term, e_index, e_cmd = server.Log.get(N)
			if (e_term != self.CurrentTerm):
				continue

			server.VolatileState['commitIndex'] = N
			commitIndexChanged = True
			break

		if commitIndexChanged:
			# This has to be delayed, because we need to inform client first about successful command append
			server.Loop.call_soon(server._apply)
