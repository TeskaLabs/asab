import logging
import json
import asyncio
import pprint

import asab

from .rpc import RPC
from .server import RaftServer
from .client import RaftClient

#

L = logging.getLogger(__name__)

#

class RaftService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.Loop = app.Loop

		# Low level communication
		self.RPC = RPC(app)

		# Raft server
		#TODO: Optional ...
		self.Server = RaftServer(app, self.RPC)

		# Raft client
		self.Client = RaftClient(app, self.RPC)


	async def initialize(self, app):
		await self.Server.initialize(app)


	async def finalize(self, app):
		await self.Server.finalize(app)

