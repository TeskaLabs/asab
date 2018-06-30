import asyncio

class Peer(object):

	def __init__(self, address):
		self.Address = address # None for self
		self.Id = '?'
		self.VoteGranted = False
		self.RPCdue = None

		self.Online = '?'

		# Following entries are valid only for a leader (reinitialize after election)
		self.nextIndex = None
		self.matchIndex = None
		self.logReadyEvent = None
