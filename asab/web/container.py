import re
import logging

import aiohttp
import aiohttp.web

import typing

from .accesslog import AccessLogger
from ..config import Configurable
from ..tls import SSLContextBuilder
from .service import WebService
from ..application import Application

#

L = logging.getLogger(__name__)

#


class WebContainer(Configurable):
	"""
	Configurable object that serves as a backend for `asab.WebService`.
	It contains everything needed for the web server existence, namely all the configuration and the server Application object.
	"""

	ConfigDefaults = {
		'listen': '0.0.0.0 8080',  # Can be multiline
		'backlog': 128,
		'rootdir': '',
		'servertokens': 'full',  # Controls whether 'Server' response header field is included ('full') or faked 'prod' ()
		'cors': '',
		'cors_preflight_paths': '/openidconnect/*, /test/*',
		'body_max_size': 1024**2,  # Client’s maximum body size in a request, in bytes
	}


	def __init__(self, websvc: WebService, config_section_name: str, config: typing.Optional[dict] = None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.Addresses = None  # The address is available only after `WebContainer.started!` PubSub message is published.
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

			if all([c in '0123456789' for c in line[0]]):
				# If the first item is a number, consider that a port number
				addr = ["0.0.0.0", "::"]  # We want to listen on IPv4 and IPv6
				port = line.pop(0).strip()
				port = int(port)
			else:
				# First item is a port, a second is an IP address of the network interface to listen to
				addr = line.pop(0).strip()
				port = line.pop(0).strip()
				port = int(port)
			ssl_context = None

			for param in line:
				if param.startswith('ssl:'):
					# Dedicated section for SSL
					ssl_context = SSLContextBuilder(param, config=self.Config).build()
					# SSL parameters are included in the current config section
				elif param.startswith('ssl'):
					ssl_context = SSLContextBuilder("<none>", config=self.Config).build()
				else:
					raise RuntimeError(
						"Unknown listen parameter in section [{}]: {}".format(config_section_name, param)
					)

			if isinstance(addr, list):
				for a in addr:
					self._listen.append((a, port, ssl_context))
			else:
				self._listen.append((addr, port, ssl_context))

		if len(self._listen) == 0:
			L.warning("Missing configuration.")

		client_max_size = int(self.Config.get("body_max_size"))
		self.WebApp: aiohttp.web.Application = aiohttp.web.Application(client_max_size=client_max_size)
		"""
		The Web Application object. See [aiohttp documentation](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=Application#application) for the details.

		It is a *dict-like* object, so you can use it for sharing data globally by storing arbitrary properties for later access from a handler.

		Attributes:
			WebApp["app"] (asab.Application): Reference to the ASAB Application.

			WebApp["rootdir"] (asab.web.staticdir.StaticDirProvider): Reference to the root path specified by `rootdir` configuration.
		"""
		self.WebApp.on_response_prepare.append(self._on_prepare_response)
		self.WebApp['app'] = websvc.App

		rootdir = self.Config.get("rootdir")
		if len(rootdir) > 0:
			from .staticdir import StaticDirProvider
			self.WebApp['rootdir'] = StaticDirProvider(self.WebApp, root='/', path=rootdir)

		access_log = logging.getLogger(__name__[:__name__.rfind('.')] + '.al')
		access_log.App = websvc.App

		self.WebAppRunner = aiohttp.web.AppRunner(
			self.WebApp,
			handle_signals=False,
			access_log=access_log,
			access_log_class=AccessLogger,
		)

		websvc._register_container(self, config_section_name)

		if self.CORS != "":
			preflight_str = self.Config["cors_preflight_paths"].strip("\n").replace("*", "{tail:.*}")
			preflight_paths = re.split(r"[,\s]+", preflight_str, re.MULTILINE)
			self.add_preflight_handlers(preflight_paths)


	async def _start(self, app: Application):
		await self.WebAppRunner.setup()

		for addr, port, ssl_context in self._listen:
			site = aiohttp.web.TCPSite(
				self.WebAppRunner,
				host=addr, port=port, backlog=self.BackLog,
				ssl_context=ssl_context,
			)
			await site.start()

			if isinstance(site, aiohttp.web_runner.TCPSite):
				for address in site._runner.addresses:
					if self.Addresses is None:
						self.Addresses = []
					self.Addresses.append(address)

		self.WebApp['app'].PubSub.publish("WebContainer.started!", self)


	async def _stop(self, app: Application):
		self.WebApp['app'].PubSub.publish("WebContainer.stopped!", self)
		await self.WebAppRunner.cleanup()


	def add_preflight_handlers(self, preflight_paths: typing.List[str]):
		"""
		Add handlers with preflight resources.

		Preflight requests are sent by the browser, for some cross domain request (custom header etc.).
		Browser sends preflight request first.
		It is request on the same endpoint as app demanded request, but of **OPTIONS** method.
		Only when satisfactory response is returned, browser proceeds with sending original request.
		Use `cors_preflight_paths` option to specify all paths and path prefixes (separated by comma) for which you
		want to allow **OPTIONS** method for preflight requests.

		Args:
			preflight_paths (list[str]): List of routes that will be provided with **OPTIONS** handler.
		"""
		for path in preflight_paths:
			self.WebApp.router.add_route("OPTIONS", path, self._preflight_handler)


	async def _preflight_handler(self, request):
			return aiohttp.web.HTTPNoContent(headers={
				"Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
				"Access-Control-Allow-Methods": "GET, POST, OPTIONS",
				"Access-Control-Allow-Headers": "X-PINGOTHER, Content-Type, Authorization",
				"Access-Control-Allow-Credentials": "true",
				"Access-Control-Max-Age": "86400",
			})


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens

		if self.CORS != "":
			# TODO: Be more precise about "allow origin" header
			response.headers['Access-Control-Allow-Origin'] = "*"
			response.headers['Access-Control-Allow-Methods'] = "GET, POST, DELETE, PUT, PATCH, OPTIONS"


	def get_ports(self) -> typing.List[str]:
		"""
		Return list of available ports.

		Returns:
			list[str]: List of ports.
		"""
		ports = []
		for addr, port, ssl_context in self._listen:
			ports.append(port)
		return ports
