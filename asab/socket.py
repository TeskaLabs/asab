from .abc.service import Service

class StreamSocketServerService(Service):


	def __init__(self, app):
		super().__init__(app)
		self._servers = []
		app.PubSub.subscribe("Application.exit!", self._on_exit)


	async def create_server(self, app, protocol, host, port):
		server = await app.Loop.create_server(protocol, host, port)
		self._servers.append(server)


	def _on_exit(self, event_name):
		for server in self._servers:
			server.close()


	async def finalize(self, app):
		#TODO: Paraelize this ...
		for server in self._servers:
			await server.wait_closed()
