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

[ssl:web]
cert=...
key=...
...


## Multiple interfaces, one with HTTPS (inline)

[web]
listen:
	0.0.0.0 8080
	:: 8080
	0.0.0.0 8443 ssl
	0.0.0.0:8001

# The SSL parameters are inside of the WebContainer section
cert=...
key=...

...

# Preflight paths
Preflight requests are sent by the browser, for some cross domain request (custom header etc.).
Browser sends preflight request first. It is request on same endpoint as app demanded request, but of OPTIONS method.
Only when satisfactory response is returned, browser proceeds with sending original request.
Use `preflightpaths` to specify all paths and path prefixes (separated by comma) for which you
want to allow OPTIONS method for preflight requests.
	'''


	ConfigDefaults = {
		'listen': '0.0.0.0 8080',  # Can be multiline
		'backlog': 128,
		'rootdir': '',
		'servertokens': 'full',  # Controls whether 'Server' response header field is included ('full') or faked 'prod' ()
		'cors': '',
		'preflightpaths': '/openidconnect/*, /test/*',
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
					# Dedicated section for SSL
					ssl_context = SSLContextBuilder(param).build()
					# SSL parameters are included in the current config section
				elif param.startswith('ssl'):
					ssl_context = SSLContextBuilder("<none>", config=self.Config).build()
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

		if self.CORS != "":
			preflight_str = self.Config.get("preflightpaths")
			preflight_paths = preflight_str.replace(" ", "").replace("*", "{tail:.*}").split(",")
			self.add_preflight_handlers(preflight_paths)


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


	def add_preflight_handlers(self, preflight_paths):
		for path in preflight_paths:
			self.WebApp.router.add_route("OPTIONS", path, self.preflight_handler)


	async def preflight_handler(self, request):
			return aiohttp.web.HTTPNoContent(headers={
				"Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
				"Access-Control-Allow-Methods": "GET, POST, OPTIONS",
				"Access-Control-Allow-Headers": "X-PINGOTHER, Content-Type, Authorization",
				"Access-Control-Allow-Credentials": "true",
				"Access-Control-Max-Age": "86400",
			})

	async def finalize(self, app):
		await self.WebAppRunner.cleanup()


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens

		if self.CORS == "*":
			response.headers['Access-Control-Allow-Origin'] = "*"
			response.headers['Access-Control-Allow-Methods'] = "GET, POST, DELETE, PUT, PATCH, OPTIONS"
		elif self.CORS != "":
			# TODO: Be more precise about "allow origin" header
			response.headers['Access-Control-Allow-Origin'] = "*"
			response.headers['Access-Control-Allow-Methods'] = "GET, POST, DELETE, PUT, PATCH, OPTIONS"


	def get_ports(self):
		ports = []
		for addr, port, ssl_context in self._listen:
			ports.append(port)
		return ports

