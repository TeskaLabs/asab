import logging
import socket
import functools
import json
import asyncio
import pprint

import asab

from .rpc import RPC, RPCMethod

#

L = logging.getLogger(__name__)

#

class RaftService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.Loop = app.Loop
		self.PrimarySocket = None
		self.Sockets = {}
		self.Peers = set([])

		self.RPC = RPC(self)

		self.PersistentState = {
			'currentTerm': 0,
			'votedFor': None,
			'log': [],
		}

		self.VolatileState = {
			'commitIndex': 0,
			'lastApplied': 0,
		}

		# Parse listen address(es), can be multiline configuration item
		ls = asab.Config["asab:raft"]["listen"]
		for l in ls.split('\n'):
			l = l.strip()
			if len(l) == 0: continue
			addr, port = l.split(' ', 1)
			port = int(port)

			s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
			s.setblocking(0)
			s.bind((addr,port))

			self.Loop.add_reader(s, functools.partial(self.RPC.on_recv, s))
			self.Sockets[s.fileno()] = s

			if self.PrimarySocket is None:
				self.PrimarySocket = s

		assert(self.PrimarySocket is not None)
		self.ServerId = "{}:{}".format(socket.gethostname(), self.PrimarySocket.getsockname()[1])

		# Parse peers
		ps = asab.Config["asab:raft"]["peers"]
		for p in ps.split('\n'):
			p = p.strip()
			if len(p) == 0: continue
			addr, port = p.split(' ', 1)
			port = int(port)

			self.Peers.add((addr, port))


		assert(len(self.Peers) > 0)

		# Eh ...
		app.PubSub.subscribe("Application.tick!", self._on_tick)

	#

	def _on_tick(self, message_type):
		for peer in self.Peers:
			self.append_entries(peer)


	def append_entries(self, peer):
		#TODO: Assert that we are leader b/c append entries can be sent only be a leader
		self.RPC.call(peer, "AppendEntries",{
			"term": self.PersistentState['currentTerm'],
			"leaderId": self.ServerId,
			"prevLogIndex": 1,
			"prevLogTerm": 1,
			"entries": [],
			"leaderCommitIndex": self.VolatileState['commitIndex']
		})


	@RPCMethod("AppendEntries")
	def append_entries_server(self, params):
		term = params['term']
		leaderId = params['leaderId']

		pprint.pprint(params)



	def request_vote(self, peer):
		self.RPC.call(peer, "RequestVote",{
			"term": self.PersistentState['currentTerm'],
			"candidateId": self.ServerId,
			"lastLogIndex": 1,
			"lastLogTerm": 1,
		})


	@RPCMethod("RequestVote")
	def request_vote_server(self, params):
		term = params['term']
		candidateId = params['candidateId']

		ret = {'term': self.PersistentState['currentTerm'], 'voteGranted': False}

		if (term < self.PersistentState['currentTerm']):
			return ret

		if (self.PersistentState['votedFor'] is not None) and (self.PersistentState['votedFor'] != candidateId):
			return ret

		self.PersistentState['votedFor'] = candidateId
		ret['voteGranted'] = True

		L.warn("Voted for '{}'".format(candidateId))

		return ret


