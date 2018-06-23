import pprint
import asyncio
import logging
import itertools
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
		self.ConnectionEvent = asyncio.Event(loop=app.Loop)

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

		self.disconnect()



	async def initialize(self, app):
		#TODO: Conditionally await self.connect()
		pass


	async def connect(self):
		self.disconnect()

		if len(self.Discovery) == 0:
			L.warn("Discovery set is empty :-(")
			return

		self.LeaderAddress, self.ClientId = await self._leader_discovery()
		self.RequestSeq = itertools.count(start=1, step=1)
		self.ConnectionEvent.set()

		L.warn("Received client id '{}'".format(self.ClientId))


	def disconnect(self):
		self.LeaderAddress = None
		self.ClientId = None
		self.ConnectionEvent.clear()


	async def _leader_discovery(self):
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


	async def issue_command(self, command):

		if not self.ConnectionEvent.is_set():
			await self.connect()
			if self.LeaderAddress is None:
				raise RuntimeError("Raft client is not configured.")

			# Wait for a connection (1 second)
			await asyncio.wait_for(self.ConnectionEvent.wait(), 1.0, loop=self.Loop)
			if self.LeaderAddress is None:
				raise RuntimeError("Raft client is not configured.")

		assert(self.ClientId is not None)
		assert(self.LeaderAddress is not None)

		try:
			result = await self.RPC.acall(self.LeaderAddress, "ClientRequest", {
				'clientId': self.ClientId,
				'sequenceNum': next(self.RequestSeq),
				'command': command,
			})
		except asyncio.TimeoutError:
			L.warn("Timeout when issuing command to a '{}'".format(self.LeaderAddress))
			self.disconnect()
			raise

		except Exception as e:
			L.exception("Error in ClientRequest RPC")
			raise

		status = result.get('status', '?')

		print(">>> ClientRequest", result)
