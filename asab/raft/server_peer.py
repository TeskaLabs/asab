import asyncio
import socket

class Peer(object):

	def __init__(self, address):

		addr, port = address.split(' ', 1)
		self.Port = int(port)
		self.NonResolvedAddress = addr.strip()

		self.Address = None
		self.Me = False # Will be evaluated during a candidate state

		self.Id = '?'
		self.VoteGranted = False
		self.RPCdue = None

		self.Online = '?'

		# Following entries are valid only for a leader (reinitialize after election)
		self.nextIndex = None
		self.matchIndex = None
		self.logReadyEvent = None


	def is_me(self):
		return self.Me


	def resolve(self, rpc):
		addr = socket.gethostbyname(self.NonResolvedAddress)
		self.Address = (addr, self.Port)
