import logging
import aiohttp.web
import aiohttp.web_response
import asab

#

L = logging.getLogger(__name__)

#

class WebService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		servertokens = asab.Config["asab:web"]["servertokens"]
		if servertokens == 'prod':
			# Because we cannot remove token completely
			self.ServerTokens = "asab"
		else:
			from .. import __version__
			self.ServerTokens = aiohttp.web_response.SERVER_SOFTWARE + " asab/" + __version__

		# Parse listen address(es), can be multiline configuration item
		ls = asab.Config["asab:web"]["listen"]
		self._listen = []
		for l in ls.split('\n'):
			addr, port = l.split(' ', 1)
			port = int(port)
			self._listen.append((addr, port))

		self.WebApp = aiohttp.web.Application(loop=app.Loop)
		self.WebApp.on_response_prepare.append(self._on_prepare_response)
		self.WebApp['app'] = app

		rootdir = asab.Config["asab:web"]["rootdir"]
		if len(rootdir) > 0:
			from .staticdir import StaticDirProvider
			self.WebApp['rootdir'] = StaticDirProvider(self, root='/', path=rootdir)

		self.WebAppRunner = aiohttp.web.AppRunner(self.WebApp, handle_signals=False)


	async def initialize(self, app):

		await self.WebAppRunner.setup()

		for addr, port in self._listen:
			site = aiohttp.web.TCPSite(self.WebAppRunner, addr, port)
			await site.start()


	async def finalize(self, app):
		await self.WebAppRunner.cleanup()


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens


	def add_frontend_web_app(self, root, path, index='index.html'):
		'''
To serve e.g. React or AngularJS frontend web application,
add this to your asab.Application / async def initialize(self):

websvc = self.get_service("asab.WebService")
webappdir = os.environ.get('WEBAPPDIR', 'webapp')
websvc.add_frontend_web_app('/', webappdir)
		'''
		from .staticdir import StaticDirProvider
		StaticDirProvider(self, root=root, path=path, index=index)
