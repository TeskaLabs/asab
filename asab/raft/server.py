import random
import os
import socket
import logging
import pprint

import asab

from .rpc import RPCMethod, RPCDelayedReply, RPCError
from .server_states import FollowerState, CandidateState, LeaderState
from .server_peer import Peer
from .log import Log
from .common import StatusCode, guess_my_ip_address

#

L = logging.getLogger(__name__)

#

class RaftServer(object):


	def __init__(self, app, rpc):
		self.Loop = app.Loop
		self.State = None
		self.LeaderAddress = None
		self.Peers = []

		self.RPC = rpc
		self.RPC.bind(self)

		self.PubSub = app.PubSub

		self.Id = asab.Config["asab:raft"]["server_id"]
		if self.Id == "" or self.Id is None:
			self.Id = "{}:{}".format(socket.gethostname(), rpc.PrimarySocket.getsockname()[1])

		self.ElectionTimerRange = (
			asab.Config["asab:raft"].getint("election_timeout_min"),
			asab.Config["asab:raft"].getint("election_timeout_max")
		)
		assert(self.ElectionTimerRange[0] < self.ElectionTimerRange[1])
		self.ElectionTimer = asab.Timer(self._on_election_timeout, loop=self.Loop)

		self.HeartBeatTimeout = asab.Config["asab:raft"].getint("heartbeat_timeout") / 1000.0

		var_dir = asab.Config['general']['var_dir']
		self.PersistentState = asab.PersistentDict(os.path.join(var_dir, '{}.raft'.format(self.Id.replace('.','-'))))
		self.PersistentState.setdefault('currentTerm', 0)
		self.PersistentState.setdefault('votedFor', None)
		
		# 
		# https://github.com/ongardie/dissertation#readme Errata:
		# Although lastApplied is listed as volatile state, it should be as volatile as the state machine.
		# If the state machine is volatile, lastApplied should be volatile.
		# If the state machine is persistent, lastApplied should be just as persistent.
		self.PersistentState.setdefault('lastApplied', 0)

		self.Log = Log(os.path.join(var_dir, '{}.raftlog'.format(self.Id.replace('.','-'))))

		# Volatile State
		self.CommitIndex = 0


	async def initialize(self, app, client, bootstrapping=False):
		'''
		`bootstrap` specifies if the cluster is bootstrapping, hence the routine of how to get peers is different
		`client` is Raft client, available only if not bootstrapping
		'''

		if not bootstrapping:
			assert(len(self.Peers) == 0)			
			s = await client.add_server()
			#for peer in s.get('peers'):
			#	self.Peers.append(Peer(peer.get('address')))

		else:
			addr, port = self.RPC.PrimarySocket.getsockname()
			
			if addr == '0.0.0.0':
				# Listen on all interfaces found, we need to get more specific 
				addrs = sorted([address for family, address in guess_my_ip_address(self.RPC) if family == self.RPC.PrimarySocket.family])
				if len(addrs) == 0:
					L.error("Cannot find the server IP address")
					return
				addr = addrs[0]

			self.Peers.append(Peer("{} {}".format(addr, port)))

		# Enter follower state
		self.State = FollowerState(self)


	async def finalize(self, app):
		if self.State is not None:
			await self.State.finalize(app)
		self.ElectionTimer.stop()

	#

	def _apply(self):
		'''
		If commitIndex > lastApplied: increment lastApplied, apply log[lastApplied] to state machine
		'''
		lastApplied = self.PersistentState['lastApplied']

		while self.CommitIndex > lastApplied:
			n = lastApplied + 1
			_, _, command = self.Log.get(n)
			print("APPLY: {} {}".format(n, command))
			self.PubSub.publish("Raft.apply!", command=command)
			self.PersistentState['lastApplied'] = lastApplied = n

			delayed_reply = self.RPC.pop_delayed_reply(("client_request", n))
			if delayed_reply is not None:
				delayed_reply.execute(command=command)

	#

	def get_election_timeout(self):
		'''
		Get randomized election timeout in miliseconds
		'''
		return random.randint(*self.ElectionTimerRange) / 1000.0	

	#

	async def _on_election_timeout(self):
		self.State = CandidateState(self)


	def evalute_election(self):
		if isinstance(self.State, LeaderState):
			# Already a leader
			return True

		if isinstance(self.State, FollowerState):
			L.warn("We are follower, cannot evaluate election")
			return False

		voted_yes = 0
		voted_no = 0
		for peer in self.Peers:
			if peer.VoteGranted:
				voted_yes += 1
			else:
				voted_no += 1

		# A candidate wins an election if it receives votes from a majority of the servers in the full cluster for the same term.
		if voted_yes > voted_no:
			self.State = LeaderState(self)
			return True

		return False

	#

	def _convert_to_follower(self, term):
		'''
		If term in RPC request or response is higher than current term, convert to follower
		'''
		assert(self.State.CurrentTerm < term)
		self.PersistentState['currentTerm'] = self.State.CurrentTerm = term
		if not isinstance(self.State, FollowerState):
			self.State = FollowerState(self)


	@RPCMethod("AppendEntries")
	def append_entries(self, peer_address, params):
		'''
		This is server-side of the method
		'''
		term = params['term']
		leaderId = params['leaderId']

		entries = params['entries']
		prevLogTerm = params['prevLogTerm']
		prevLogIndex = params['prevLogIndex']

		leaderCommit = params['leaderCommit']

		ret = {
			'term': self.State.CurrentTerm,
			'success': False,
			'serverId': self.Id,
			'matchIndex': self.Log.Index,
		}

		if term > self.State.CurrentTerm:
			L.warn("Current term synced from {} to {}".format(self.State.CurrentTerm, term))
			self._convert_to_follower(term)
			ret['term'] = term

		elif term < self.State.CurrentTerm:
			L.warning("Received AppendEntries for an old term:{} when current term is {}".format(term, self.State.CurrentTerm))
			return ret

		else:
			self.ElectionTimer.restart(self.get_election_timeout())

		assert(isinstance(self.State, FollowerState))
		self.LeaderAddress = peer_address

		if (len(entries) == 0) and (prevLogTerm == 0) and (prevLogIndex == 0):
			# This is special case for ping-only append entries
			ret['success'] = True

		# TODO: Better prev check (including the term)
		elif self.Log.Index == prevLogIndex:
			if len(entries) > 0:
				self.Log.replicate(self.State.CurrentTerm, entries)
				#self.Log.print()
			ret['success'] = True

			#If leaderCommit > commitIndex, set commitIndex = min(leaderCommit, index of last new entry)
			if leaderCommit > self.CommitIndex:
				self.CommitIndex = min(leaderCommit, self.Log.Index)
				self._apply()

		else:
			L.warn("My log index:{} vs prevLogIndex:{} (len(entries):{})".format(self.Log.Index, prevLogIndex, len(entries)))
		
		return ret

	#

	@RPCMethod("RequestVote")
	def request_vote(self, peer_address, params):
		'''
		This is server-side of the method
		'''
		term = params['term']
		candidateId = params['candidateId']
		lastLogIndex = params['lastLogIndex']
		lastLogTerm = params['lastLogTerm']

		votedFor = self.PersistentState['votedFor']

		ret = {
			'term': term,
			'voteGranted': False,
			'serverId': self.Id,
		}

		if term < self.State.CurrentTerm:
			# Reply false if term < currentTerm
			return ret

		elif term > self.State.CurrentTerm:
			# If RPC request or response contains term T > currentTerm: set currentTerm = T, convert to follower
			self._convert_to_follower(term)
			self.PersistentState['votedFor'] = votedFor = candidateId
			ret['voteGranted'] = True
			L.warn("Voted for '{}' in {} term (higher term)".format(candidateId, term))

		# If votedFor is null or candidateId, and candidate’s log is at least as up-to-date as receiver’s log, grant vote
		if (votedFor is not None) and (votedFor != candidateId):
			return ret # We already voted for someone else

		myLastLogTerm, myLastLogIndex, _ = self.Log.get_last()
		if (myLastLogTerm > lastLogTerm) or (myLastLogIndex > lastLogIndex):
			return ret # Our log is more recent that the candidate

		ret['voteGranted'] = True
		if votedFor is None:
			self.PersistentState['votedFor'] = candidateId
			L.warn("Voted for '{}' in {} term (not voted)".format(candidateId, term))
		else:
			L.warn("Voted for '{}' in {} term (confirm vote)".format(candidateId, term))

		if isinstance(self.State, CandidateState):
			# This could be own call to self (candidate queries its own to get vote)
			if candidateId != self.Id:
				self.State = FollowerState(self)

		else:
			assert(isinstance(self.State, FollowerState))
			self.ElectionTimer.restart(self.get_election_timeout())

		return ret


	# Client API

	def _assert_leader(self):
		'''
		Handles the API request that requires a leader.
		If a call is received by a peer in other state (e.g. candidate or follower), the error with NOT_LEADER status is raised
		'''
		if not isinstance(self.State, LeaderState):
			data = {}
			if self.LeaderAddress is not None:
				data["leaderHint"] = self.LeaderAddress
			raise RPCError(
				code=StatusCode.NOT_LEADER,
				message="Not Leader",
				data=data if len(data) > 0 else None
			)


	@RPCMethod("RegisterClient")
	def register_client(self, peer_address, params):
		'''
		This is server-side of the method
		'''
		self._assert_leader()
		ret = {
			"clientId": "TODO",
			"peerAddress": peer_address, # Indicate the aparent peer address
		}
		return ret



	@RPCMethod("ClientRequest")
	def client_request(self, peer_address, params):
		'''
		This is server-side of the method
		'''
		self._assert_leader()

		if params is None: params = {}
		clientId = params.get("clientId")
		sequenceNum = params.get("sequenceNum")
		command = params.get("command")

		if (clientId is None) or (sequenceNum is None) or (command is None):
			L.warn("Received invalid ClientRequest")
			return

		# Append command to a log
		log_index = self.State.append_command(self, command)

		class ClientRequestReply(RPCDelayedReply):

			def __init__(self):
				super().__init__(("client_request", log_index))

			def reply(self, *args, **kwargs):
				ret = {
					"result": "NOT-IMPLEMENTED-YET",
				}
				return ret

		raise ClientRequestReply()


	@RPCMethod("Status")
	def status(self, peer_address, params):
		self._assert_leader()

		currentTerm, votedFor, lastApplied = self.PersistentState.load('currentTerm','votedFor', 'lastApplied')

		ret = {
			"id": self.Id,
			"state": self.State.Name,

			"currentTerm": currentTerm,

			"commitIndex": self.CommitIndex,
			"lastApplied": lastApplied,
		}

		if isinstance(self.State, LeaderState):
			peers = []
			for p in self.Peers:
				peers.append({
					'address': p.Address,
					'id': p.Id,
					'online': p.Online,
					'voteGranted': p.VoteGranted,
					'rpcDue': p.RPCdue,
					'nextIndex': p.nextIndex,
					'matchIndex': p.matchIndex,
					'is_me': p.is_me(),
				})
			ret['peers'] = peers

		return ret


	@RPCMethod("AddServer")
	def add_server(self, peer_address, params):
		self._assert_leader()
