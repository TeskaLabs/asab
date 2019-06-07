import asyncio
import socket

class Peer(object):

	def __init__(self, address):

		if isinstance(address, str):
			addr, port = address.split(' ', 1)

		elif isinstance(address, list) or isinstance(address, tuple):
			assert(len(address) == 2)
			addr = address[0]
			port = address[1]

		else:
			raise RuntimeError("Invalid type of the address, should be string, tuple or list")

		self.NonResolvedAddress = addr.strip()
		self.Port = int(port)

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
		# TODO: `socket.gethostbyname` call should be ideally non-blocking
		addr = socket.gethostbyname(self.NonResolvedAddress)
		self.Address = (addr, self.Port)
