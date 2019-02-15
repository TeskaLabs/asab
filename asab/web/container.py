import re
import asyncio
import logging
import aiohttp

from ..config import ConfigObject
from ..net import SSLContextBuilder
from .accesslog import AccessLogger


class WebContainer(ConfigObject):


	ConfigDefaults = {
		'listen': '0.0.0.0:8080', # Can be multiline
		'backlog': 128,
		'rootdir': '',
		'servertokens': 'full', # Controls whether 'Server' response header field is included ('full') or faked 'prod' ()
		# + SSL key/values from SSLContextBuilder
	}


	def __init__(self, websvc, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)

		if 'ssl:cert' in self.Config:
			builder = SSLContextBuilder(config_section_name, config=config)
			self.SSLContext = builder.build()
		else:
			self.SSLContext = None

		self.BackLog = int(self.Config.get("backlog"))

		servertokens = self.Config.get("servertokens")
		if servertokens == 'prod':
			# Because we cannot remove token completely
			self.ServerTokens = "asab"
		else:
			from .. import __version__
			self.ServerTokens = aiohttp.web_response.SERVER_SOFTWARE + " asab/" + __version__

		# Parse listen address(es), can be multiline configuration item
		ls = self.Config.get("listen")
		self._listen = []
		for line in ls.split('\n'):
			line = line.strip()
			if len(line) == 0: continue
			# Split the last token (separated by a ' ' or ':')
			addr, port, _ = re.split(r"[: ](\d+)$", line)
			port = int(port)
			self._listen.append((addr, port))

		self.WebApp = aiohttp.web.Application(loop=websvc.App.Loop)
		self.WebApp.on_response_prepare.append(self._on_prepare_response)
		self.WebApp['app'] = websvc.App

		rootdir = self.Config.get("rootdir")
		if len(rootdir) > 0:
			from .staticdir import StaticDirProvider
			self.WebApp['rootdir'] = StaticDirProvider(self.WebApp, root='/', path=rootdir)

		self.WebAppRunner = aiohttp.web.AppRunner(
			self.WebApp,
			handle_signals=False,
			access_log=logging.getLogger(__name__[:__name__.rfind('.')] + '.al'),
			access_log_class=AccessLogger,
		)

		websvc._register_container(self, config_section_name)


	async def initialize(self, app):
		await self.WebAppRunner.setup()

		for addr, port in self._listen:
			site = aiohttp.web.TCPSite(self.WebAppRunner,
				host=addr, port=port, backlog=self.BackLog,
				ssl_context = self.SSLContext,
			)
			await site.start()


	async def finalize(self, app):
		await self.WebAppRunner.cleanup()


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens

		