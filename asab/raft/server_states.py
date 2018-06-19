import abc
import logging

#

L = logging.getLogger(__name__)

#

class StateABC(abc.ABC):

	def __init__(self, server):
		# Used as cache of current term over server.PersistentState['currentTerm']
		self.CurrentTerm = server.PersistentState['currentTerm']
		L.warn("Entering {} state from {} in term {}".format(self, server.State, self.CurrentTerm))


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
				self.request_vote(server, peer)
			else:
				peer.VoteGranted = True

		#TODO: Maybe call soon server.evalute_election()
		# Can candidate goes immediatelly into a leader state?


	def on_heartbeat_timeout(self, server):
		# Send RequestVote RCP to all peers but myself
		for peer in server.Peers:
			if peer.Address is not None:
				self.request_vote(server, peer)


	def request_vote(self, server, peer):
		'''
		The request is sent
		'''
		server.RPC.call(peer.Address, "RequestVote",{
			"term": self.CurrentTerm,
			"candidateId": server.Id,
			"lastLogIndex": 1,
			"lastLogTerm": 1,
			"timestamp": server.Loop.time(),
		})


	def request_vote_result(self, server, peer_address, params):
		term = params['term']
		voteGranted = params['voteGranted']
		serverId = params['serverId']

		if (term < self.CurrentTerm):
			return
		elif (term > self.CurrentTerm):
			L.warning("Received RequestVote result for term {} higher than current term {}".format(term, self.CurrentTerm))
			return

		for peer in server.Peers:
			if peer.Address == peer_address:
				if peer.Id == '?':
					L.warn("Peer at '{}' is now known as '{}'".format(peer_address, serverId))
					peer.Id = serverId
				elif peer.Id != serverId:
					L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer_address))

				if voteGranted:
					if not peer.VoteGranted:
						peer.VoteGranted = True
						server.evalute_election()
					else:
						L.warn("Peer '{}'/'{}' already voted".format(peer_address, serverId))

				peer.RPCdue = server.Loop.time() - params['timestamp']
				break
		else:
			L.warn("Cannot find peer entry for '{}' / '{}'".format(peer_address, serverId))


#

class LeaderState(StateABC):

	Name = "Leader"

	def __init__(self, server):
		super().__init__(server)
		server.ElectionTimer.stop()
		server.HeartBeatTimer.restart(server.HeartBeatTimeout)

		self.send_heartbeat(server)


	def on_heartbeat_timeout(self, server):
		self.send_heartbeat(server)


	def send_heartbeat(self, server):
		for peer in server.Peers:
			if peer.Address is not None:
				self.append_entries(peer, server)


	def append_entries(self, peer, server):
		server.RPC.call(peer.Address, "AppendEntries",{
			"term": self.CurrentTerm,
			"leaderId": server.Id,
			"prevLogIndex": 1,
			"prevLogTerm": 1,
			"entries": [],
			"leaderCommitIndex": server.VolatileState['commitIndex'],
			"timestamp": server.Loop.time(),
		})


	def append_entries_result(self, server, peer_address, params):
		serverId = params['serverId']

		for peer in server.Peers:
			if peer.Address == peer_address:
				if peer.Id == '?':
					L.warn("Peer at '{}' is now known as '{}'".format(peer_address, serverId))
					peer.Id = serverId
				elif peer.Id != serverId:
					L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer_address))

				peer.RPCdue = server.Loop.time() - params['timestamp']
				break


