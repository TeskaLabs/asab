
class Peer(object):

	def __init__(self, address):
		self.Address = address # None for self
		self.Id = '?'
		self.VoteGranted = False
		self.RPCdue = None
