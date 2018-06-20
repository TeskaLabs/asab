import pprint
import asyncio
import logging
import random

import asab

#

L = logging.getLogger(__name__)

#

class RaftClient(object):


	def __init__(self, app, rpc):
		self.Loop = app.Loop
		self.LeaderAddress = None
		self.ClientId = None

		self.RPC = rpc
		self.RPC.bind(self)


		# The discovery set contains a network addresses of the possible cluster members
		# It will be used in a leader discovery procedure.
		self.Discovery = set([])
		# Parse discovery set
		ds = asab.Config["asab:raft"]["discovery"]
		for d in ds.split('\n'):
			d = d.strip()
			if len(d) == 0: continue
			addr, port = d.split(' ', 1)
			port = int(port)
			addr = addr.strip()

			if addr is not None:
				self.Discovery.add((addr, port))


	async def initialize(self, app):
		await self.connect(app)


	async def connect(self, app):
		self.LeaderAddress = None
		self.ClientId = None

		if len(self.Discovery) == 0:
			L.warn("Discovery set is empty :-(")
			return

		self.LeaderAddress, self.ClientId = await self._leader_discovery(app)
		L.warn("Received client id '{}'".format(self.ClientId))


	async def _leader_discovery(self, app):
		'''
		Implementation of the leader discovery procedure
		'''

		class DiscoveryIterator(object):
			# Generate an infinite list (iterator) of server for a discovery.
			# It consists of partitions with unique servers separated by None that is meant for discovery cool down
			# [server1, server2, server3, None, server3, server1, server2, None, server2, ...]
			
			def __init__(self, client):
				self.Client = client
				self.PriorityAddresses = []

			def __call__(self):
				while True:
					server_addresses = list(self.Client.Discovery)
					random.shuffle(server_addresses)
					for server_address in server_addresses:
						while len(self.PriorityAddresses) > 0:
							priority_address = self.PriorityAddresses.pop()
							yield priority_address
						yield server_address
					yield None

			def prioritize(self, address):
				self.PriorityAddresses.append(address)

		di = DiscoveryIterator(self)
		for server_address in di():

			if server_address is None:
				#  Cool down ...
				await asyncio.sleep(1)
				continue

			try:
				result = await self.RPC.acall(server_address, "RegisterClient") 
			except asyncio.TimeoutError:
				L.warn("Timeout in discovery procedure for a '{}'".format(server_address))
				continue

			status = result.get('status', '?')
			
			if status == 'OK':
				# We hit the leader
				L.warn("Found cluster leader at '{}'".format(server_address))
				return server_address, result.get('clientId', 'unknown-client-id')

			elif status == 'NOT_LEADER':
				leaderHint = result.get('leaderHint')
				if leaderHint is None: continue

				# Convert the list to a tuple
				if isinstance(leaderHint, list):
					assert(len(leaderHint) == 2)
					leaderHint = (leaderHint[0], leaderHint[1])

				L.warn("Received leader hint '{}'".format(leaderHint))
				di.prioritize(leaderHint)
				continue

			else:
				L.warn("Unknown status '{}' received in a leader discovery".format(status))
