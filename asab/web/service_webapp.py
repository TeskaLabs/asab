import logging
import aiohttp.web
import asab

#

L = logging.getLogger(__name__)

#

class ServiceWebApp(asab.Service):


	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		# Parse listen address(es), can be multiline configuration item
		ls = asab.Config["asab:web"]["listen"]
		self._listen = []
		for l in ls.split('\n'):
			addr, port = l.split(' ', 1)
			port = int(port)
			self._listen.append((addr, port))

		self.Servers = []
		self.WebApp = aiohttp.web.Application(loop=app.Loop)
		self.WebApp['app'] = app


	async def initialize(self, app):
		self.Servers = []
		for addr, port in self._listen:
			server = await app.Loop.create_server(self.WebApp.make_handler(), addr, port)
			self.Servers.append(server)

	#TODO: Implement finalize() where all servers are closed including all peer connections
