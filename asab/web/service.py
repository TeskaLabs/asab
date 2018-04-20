import logging
import aiohttp.web
import asab

#

L = logging.getLogger(__name__)

#

class WebService(asab.Service):

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

		rootdir = asab.Config["asab:web"]["rootdir"]
		if len(rootdir) > 0:
			from .staticdir import StaticDirProvider
			self.WebApp['rootdir'] = StaticDirProvider(self, root='/', path=rootdir)


	async def initialize(self, app):
		self.Servers = []
		for addr, port in self._listen:
			server = await app.Loop.create_server(self.WebApp.make_handler(), addr, port)
			self.Servers.append(server)

	#TODO: Implement finalize() where all servers are closed including all peer connections


	def addFrontendWebApp(self, root, path, index='index.html'):
		'''
To serve e.g. React or AngularJS frontend web application,
add this to your asab.Application / async def initialize(self):

websvc = self.get_service("asab.WebService")
webappdir = os.environ.get('WEBAPPDIR', 'webapp')
websvc.addFrontendWebApp('/', webappdir)
		'''
		from .staticdir import StaticDirProvider
		StaticDirProvider(self, root=root, path=path, index=index)
