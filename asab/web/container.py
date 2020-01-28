import logging
import re

import aiohttp

from .accesslog import AccessLogger
from ..config import ConfigObject
from ..net import SSLContextBuilder


class WebContainer(ConfigObject):

	'''
# Configuration examples

## Simple HTTP on 8080

[web]
listen=0.0.0.0 8080

## Multiple interfaces

[web]
listen:
	0.0.0.0 8080
	:: 8080


## Multiple interfaces, one with HTTPS

[web]
listen:
	0.0.0.0 8080
	:: 8080
	0.0.0.0 8443 ssl:web
	0.0.0.0:8001
	'''


	ConfigDefaults = {
		'listen': '0.0.0.0 8080',  # Can be multiline
		'backlog': 128,
		'rootdir': '',
		'servertokens': 'full',  # Controls whether 'Server' response header field is included ('full') or faked 'prod' ()
		'cors': '',
	}


	def __init__(self, websvc, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.BackLog = int(self.Config.get("backlog"))
		self.CORS = self.Config.get("cors")

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
			if len(line) == 0:
				continue

			if ' ' in line:
				line = re.split(r"\s+", line)
			else:
				# This line allows the (obsolete) format of IPv4 with ':'
				# such as "0.0.0.0:8001"
				line = re.split(r"[:\s]", line, 1)

			addr = line.pop(0).strip()
			port = line.pop(0).strip()
			port = int(port)
			ssl_context = None

			for param in line:
				if param.startswith('ssl:'):
					ssl_context = SSLContextBuilder(param).build()
				else:
					raise RuntimeError("Unknown asab:web listen parameter: '{}'".format(param))
			self._listen.append((addr, port, ssl_context))

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
		websvc.App.PubSub.subscribe("Application.run!", self.start_container)

	async def initialize(self, app):
		pass

	async def start_container(self, event_type):
		await self.WebAppRunner.setup()

		for addr, port, ssl_context in self._listen:
			site = aiohttp.web.TCPSite(
				self.WebAppRunner,
				host=addr, port=port, backlog=self.BackLog,
				ssl_context=ssl_context,
			)
			await site.start()


	async def finalize(self, app):
		await self.WebAppRunner.cleanup()


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens

		if self.CORS == "*":
			response.headers['Access-Control-Allow-Origin'] = "*"
			response.headers['Access-Control-Allow-Methods'] = "GET, POST, DELETE, PUT, PATCH, OPTIONS"
