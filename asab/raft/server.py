import random
import re
import os
import socket
import logging

import asab

from .rpc import RPCMethod, RPCResult

#

L = logging.getLogger(__name__)

#


class RaftServer(object):


	def __init__(self, app, rpc):
		self.Loop = app.Loop
		self.RPC = rpc
		self.RPC.bind(self)

		self.Id = asab.Config["asab:raft"]["server_id"]
		if self.Id == "":
			self.Id = "{}:{}".format(socket.gethostname(), rpc.PrimarySocket.getsockname()[1])

		self.State = '?' # F .. follower, C .. candidate, L .. leader and '?' for initial

		self.ElectionTimerRange = (
			asab.Config["asab:raft"].getint("election_timeout_min"),
			asab.Config["asab:raft"].getint("election_timeout_max")
		)
		assert(self.ElectionTimerRange[0] < self.ElectionTimerRange[1])
		self.ElectionTimer = asab.Timer(self._on_election_timeout, loop=self.Loop)

		self.HeartBeatTimeout = asab.Config["asab:raft"].getint("heartbeat_timeout") / 1000.0
		self.HeartBeatTimer = asab.Timer(self._on_heartbeat_timeout, loop=self.Loop)

		var_dir = asab.Config['general']['var_dir']
		self.PersistentState = asab.PersistentDict(os.path.join(var_dir, '{}.raft'.format(self.Id.replace('.','-'))))
		self.PersistentState.setdefault('currentTerm', 0)
		self.PersistentState.setdefault('votedFor', None)
		self.PersistentState.setdefault('log', [])

		self.VolatileState = {
			'commitIndex': 0,
			'lastApplied': 0,
		}


		self.Peers = []

		# Add self to peers
		p = Peer(None)
		p.set_id(self.Id)
		self.Peers.append(p)

		# Parse peers
		ps = asab.Config["asab:raft"]["peers"]
		for p in ps.split('\n'):
			p = p.strip()
			if len(p) == 0: continue
			addr, port = p.split(' ', 1)
			port = int(port)
			addr = addr.strip()

			# Try to detect 'self' among peers
			if (addr == 'localhost') or re.match(r'^127\.0+\.0+\.\d$', addr) or (addr == "::1"):
				for s in rpc.Sockets:
					if (port == rpc.PrimarySocket.getsockname()[1]):
						# Skip this peer entry ...
						addr = None

			if addr is not None:
				self.Peers.append(Peer((addr, port)))


		assert(len(self.Peers) > 0)


	async def initialize(self, app):
		self.enter_state_follower()


	async def finalize(self, app):
		self.ElectionTimer.stop()
		self.HeartBeatTimer.stop()

	#

	def get_election_timeout(self):
		'''
		Get randomized election timeout in miliseconds
		'''
		return random.randint(*self.ElectionTimerRange) / 1000.0	

	#

	def enter_state_follower(self):
		L.warn("Entering follower state (from '{}')".format(self.State))
		self.State = 'F'
		self.HeartBeatTimer.stop()
		self.ElectionTimer.restart(self.get_election_timeout())


	async def _on_election_timeout(self):
		self.enter_state_candidate()


	def enter_state_candidate(self):
		L.warn("Entering candidate state from '{}', term:{}".format(self.State, self.PersistentState['currentTerm'] + 1))

		# Starting elections
		self.State = 'C'
		self.PersistentState['currentTerm'] += 1

		for peer in self.Peers:
			if peer.Address is not None:
				peer.VoteGranted = False
				self.request_vote(peer)
			else:
				peer.VoteGranted = True

		self.evalute_election()
		if self.State == 'C':
			self.ElectionTimer.restart(self.get_election_timeout())
			self.HeartBeatTimer.restart(self.HeartBeatTimeout)


	def evalute_election(self):
		if self.State == 'L':
			# Already a leader
			return

		if self.State == 'F':
			L.warn("We are follower, cannot evaluate election")
			return

		voted_yes = 0
		voted_no = 0
		for peer in self.Peers:
			if peer.VoteGranted:
				voted_yes += 1
			else:
				voted_no += 1

		# A candidate wins an election if it receives votes from a majority of the servers in the full cluster for the same term.
		if voted_yes > voted_no:
			self.enter_state_leader()


	def enter_state_leader(self):
		L.warn("Entering leader state from '{}', term:{}".format(self.State, self.PersistentState['currentTerm']))
		self.State = 'L'

		self.ElectionTimer.stop()
		self.HeartBeatTimer.restart(self.HeartBeatTimeout)

		self.send_heartbeat()


	async def _on_heartbeat_timeout(self):
		if self.State == 'L':
			self.send_heartbeat()
		elif self.State == 'C':
			for peer in self.Peers:
				if not peer.VoteGranted:
					self.request_vote(peer)
		else:
			L.warn("No heartbeat needed for a state {}".format(self.State))
		self.HeartBeatTimer.start(self.HeartBeatTimeout)

	#

	def send_heartbeat(self):
		for peer in self.Peers:
			if peer.Address is not None:
				self.append_entries(peer)

	#

	def append_entries(self, peer):
		assert(self.State == 'L')
		self.RPC.call(peer.Address, "AppendEntries",{
			"term": self.PersistentState['currentTerm'],
			"leaderId": self.Id,
			"prevLogIndex": 1,
			"prevLogTerm": 1,
			"entries": [],
			"leaderCommitIndex": self.VolatileState['commitIndex']
		})


	@RPCMethod("AppendEntries")
	def append_entries_server(self, params):
		term = params['term']
		leaderId = params['leaderId']

		ret = {
			'term': self.PersistentState['currentTerm'],
			'success': False,
			'serverId': self.Id,
		}

		if term >= self.PersistentState['currentTerm']:
			self.PersistentState['currentTerm'] = term
		else:
			L.warning("Received AppendEntries for an old term:{} when current term is {}".format(term, self.PersistentState['currentTerm']))
			return ret

		if self.State != 'F':
			self.enter_state_follower()

		self.ElectionTimer.restart(self.get_election_timeout())

		ret['success'] = True
		return ret


	@RPCResult("AppendEntries")
	def append_entries_result(self, peer_address, params):
		'''
		The reply is received
		'''
		serverId = params['serverId']

		for peer in self.Peers:
			if peer.Address == peer_address:
				if peer.Id == '?':
					L.warn("Peer at '{}' is now known as '{}'".format(peer_address, serverId))
					peer.Id = serverId
				elif peer.Id != serverId:
					L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer_address))

				break


	def request_vote(self, peer):
		'''
		The request is sent
		'''
		self.RPC.call(peer.Address, "RequestVote",{
			"term": self.PersistentState['currentTerm'],
			"candidateId": self.Id,
			"lastLogIndex": 1,
			"lastLogTerm": 1,
		})


	@RPCResult("RequestVote")
	def request_vote_result(self, peer_address, params):
		'''
		The reply is received
		'''
		term = params['term']
		voteGranted = params['voteGranted']
		serverId = params['serverId']

		if (term < self.PersistentState['currentTerm']):
			return
		if (term > self.PersistentState['currentTerm']):
			L.warning("Received RequestVote result for term {} higher than current term {}".format(term, self.PersistentState['currentTerm']))
			return

		for peer in self.Peers:
			if peer.Address == peer_address:
				if peer.Id == '?':
					L.warn("Peer at '{}' is now known as '{}'".format(peer_address, serverId))
					peer.Id = serverId
				elif peer.Id != serverId:
					L.warn("Server id changed from '{}' to '{}' at '{}'".format(peer.Id, serverId, peer_address))

				if voteGranted:
					if not peer.VoteGranted:
						peer.VoteGranted = True
						self.evalute_election()
					else:
						L.warn("Peer '{}'/'{}' already voted".format(peer_address, serverId))
				break
		else:
			L.warn("Cannot find peer entry for '{}' / '{}'".format(peer_address, serverId))



	@RPCMethod("RequestVote")
	def request_vote_server(self, params):
		term = params['term']
		candidateId = params['candidateId']

		ret = {
			'term': term,
			'voteGranted': False,
			'serverId': self.Id,
		}

		if (term < self.PersistentState['currentTerm']):
			return ret

		if (self.PersistentState['votedFor'] is not None) and (self.PersistentState['votedFor'] != candidateId):
			return ret

		if (self.PersistentState['votedFor'] is None) or (self.PersistentState['votedFor'] != candidateId):
			#TODO: Also check that candidate log is at least as up-to-date as receiver's log

			self.PersistentState['votedFor'] = candidateId
			ret['voteGranted'] = True
			L.warn("Voted for '{}'".format(candidateId))

			if (self.State == 'C'):
				self.enter_state_follower()

		return ret

#

class Peer(object):


	def __init__(self, address):
		self.Address = address # None for self
		self.Id = '?'
		self.VoteGranted = False


	def set_id(self, id):
		self.Id = id

