from .abc.service import Service

class StreamSocketServerService(Service):

	'''
	Example of use:

	class ServiceMyProtocolServer(asab.StreamSocketServerService):

		async def initialize(self, app):
			host = asab.Config.get('http', 'host')
			port = asab.Config.getint('http', 'port')

			L.debug("Starting server on {} {} ...".format(host, port))
			await self.create_server(app, MyProtocol, [(host, port)])
	'''

	def __init__(self, app):
		super().__init__(app)
		self._servers = []
		app.PubSub.subscribe("Application.exit!", self._on_exit)


	async def create_server(self, app, protocol, addrs):
		#TODO: Paraelize this ...
		for addr in addrs:
			host, port = addr
			server = await app.Loop.create_server(protocol, host, port)
			self._servers.append(server)


	def _on_exit(self, message_type):
		for server in self._servers:
			server.close()


	async def finalize(self, app):
		#TODO: Paraelize this ...
		for server in self._servers:
			await server.wait_closed()
