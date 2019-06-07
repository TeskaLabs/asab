import asyncio
import logging
import itertools
import random

import asab

from .rpc import RPCError
from .common import StatusCode

#

L = logging.getLogger(__name__)

#

class RaftClient(object):


	def __init__(self, app, rpc):
		self.Loop = app.Loop
		self.LeaderAddress = None
		self.LeaderHint = None
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
		# Skip connect() if connection should be established in a 'lazy' mode
		# aka with a first client call
		await self.connect()


	async def connect(self):
		self.disconnect()

		if len(self.Discovery) == 0:
			L.warn("Discovery set is empty :-(")
			return False

		self.LeaderAddress, self.ClientId = await self._leader_discovery()
		self.RequestSeq = itertools.count(start=1, step=1)
		self.ConnectionEvent.set()

		L.warn("Received client id '{}'".format(self.ClientId))
		return True


	def disconnect(self):
		self.LeaderAddress = None
		self.ClientId = None
		self.ConnectionEvent.clear()


	async def _ensure_connected(self):
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


	async def _leader_discovery(self):
		'''
		Implementation of the leader discovery procedure
		'''

		class DiscoveryIterator(object):
			# Generate an infinite list (iterator) of server for a discovery.
			# It consists of partitions with unique servers separated by None that is meant for discovery cool down
			# [server1, server2, server3, None, server3, server1, server2, None, server2, ...]
			# Also, it prefers to supply address in client.LeaderHint if present
			
			def __init__(self, client):
				self.Client = client

			def __call__(self):
				while True:
					server_addresses = list(self.Client.Discovery)
					random.shuffle(server_addresses)
					for server_address in server_addresses:
						if self.Client.LeaderHint is not None:
							lh = self.Client.LeaderHint
							self.Client.LeaderHint = None
							yield lh
						yield server_address
					yield None


		di = DiscoveryIterator(self)
		for server_address in di():

			if server_address is None:
				#  Cool down ...
				await asyncio.sleep(1)
				continue

			try:
				result = await self.RPC.acall(server_address, "RegisterClient") 
				return server_address, result.get('clientId', 'unknown-client-id')

			except RPCError as e:
				if e.code == StatusCode.NOT_LEADER:

					leaderHint = e.data.get('leaderHint') if e.data is not None else None
					if leaderHint is None: continue

					# Convert the list to a tuple
					if isinstance(leaderHint, list):
						assert(len(leaderHint) == 2)
						leaderHint = (leaderHint[0], leaderHint[1])

					L.warn("Received leader hint '{}'".format(leaderHint))
					self.LeaderHint = leaderHint
					continue

				elif e.code == -32601:
					# Not a server (maybe just bootstrapping)
					L.warn("Raft server not detected at '{}'".format(server_address))
					continue

				L.exception("RPC error during discovery at a '{}'".format(server_address), e)

			except asyncio.TimeoutError:
				L.warn("Timeout in discovery at a '{}'".format(server_address))


	async def acall(self, method, params = None, *, timeout = None):
		'''
		Adaptor for RPC.acall that handles NOT_LEADER, timeouts etc.
		'''
		for n in itertools.count(1):
			await self._ensure_connected()

			try:
				return await self.RPC.acall(self.LeaderAddress, method, params, timeout=timeout)

			except RPCError as e:
				if e.code == StatusCode.NOT_LEADER:
					leaderHint = e.data.get('leaderHint') if e.data is not None else None
					if leaderHint is not None:
						# Convert the list to a tuple
						if isinstance(leaderHint, list):
							assert(len(leaderHint) == 2)
							leaderHint = (leaderHint[0], leaderHint[1])

						self.LeaderHint = leaderHint
						self.disconnect()
						continue

				L.exception("RPC error in {} RPC to '{}'".format(method, self.LeaderAddress))
				raise


			except asyncio.TimeoutError:
				if n > 2:
					raise
				L.warn("Timeout in '{}' RPC to a '{}' - retrying {}".format(method, self.LeaderAddress, n))
				self.disconnect()


			except Exception:
				L.exception("Error in {} RPC to '{}'".format(method, self.LeaderAddress))
				raise


	async def client_request(self, command):
		return await self.acall("ClientRequest", {
			'clientId': self.ClientId,
			'sequenceNum': next(self.RequestSeq),
			'command': command,
		})


	async def status(self):
		return await self.acall("Status")


	async def add_server(self):
		return await self.acall("AddServer")
