import os
import logging
import asyncio

import asab

from .rpc import RPC
from .server import RaftServer
from .client import RaftClient
from .webapi import RaftWebApi

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
		if asab.Config["asab:raft"].getboolean("server"):
			self.Server = RaftServer(app, self.RPC)
		else:
			self.Server = None

		# Raft client
		self.Client = RaftClient(app, self.RPC)

		if asab.Config["asab:raft"].getboolean("webapi"):
			self.WebApi = RaftWebApi(app, self.RPC)
		else:
			self.WebApi = None


	async def initialize(self, app):
		initialize_server_after_client = False
		if self.Server is not None:
			cluster_bootstrap = os.environ.get('CLUSTER_BOOTSTRAP')
			if cluster_bootstrap == "1":
				await self.Server.initialize(app, None, bootstrapping=True)
			else:
				initialize_server_after_client = True

		future = asyncio.ensure_future(self.Client.initialize(app), loop=app.Loop)
		# If server is to be initialized after a client is up, schedule a future for that
		if initialize_server_after_client:
			def _initialize_server_after_client(future):
				if not future.cancelled():
					asyncio.ensure_future(self.Server.initialize(app, self.Client), loop=app.Loop)
			future.add_done_callback(_initialize_server_after_client)


	async def finalize(self, app):
		if self.Server is not None:
			await self.Server.finalize(app)
		await self.RPC.finalize(app)

