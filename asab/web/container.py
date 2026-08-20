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
from ..contextvars import Request
from . import cors

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
		'cors_preflight_paths': '/*',
		'cors_allow_headers': 'Authorization, Content-Type, X-App, X-Request-Id',
		'cors_allow_methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
		'cors_allow_credentials': 'yes',
		'body_max_size': 1024**2,  # Client’s maximum body size in a request, in bytes
	}


	def __init__(self, websvc: WebService, config_section_name: str, config: typing.Optional[dict] = None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.Addresses = None  # The address is available only after `WebContainer.started!` PubSub message is published.
		self.BackLog = int(self.Config.get("backlog"))
		self.CORS = cors.normalize_cors_config(self.Config.get("cors"))
		self.CORSHandler = None
		self._CORSPreflightRoutes = set()

		servertokens = self.Config.get("servertokens")
		if servertokens == 'prod':
			# Because we cannot remove token completely
			self.ServerTokens = "asab"
		else:
			from .. import __version__
			self.ServerTokens = aiohttp.web_response.SERVER_SOFTWARE + " asab/" + __version__

		# Parse listen address(es), can be multiline configuration item
		ls = self.Config.get("listen")

		if isinstance(ls, int):
			ls = str(ls)  # Assume that the integer is a port number
		if not isinstance(ls, str):
			raise TypeError("Invalid type of 'listen' configuration item: {}".format(type(ls)))

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
			L.warning(
				"Web container has no listen address configured; HTTP server will not start.",
				struct_data={"config_section": config_section_name},
			)

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

		if self.CORS:
			self.enable_cors(allow_origin=self.CORS)

		self.WebApp.middlewares.append(set_request_context)


	async def _start(self, app: Application):
		await self.WebAppRunner.setup()

		for addr, port, ssl_context in self._listen:
			site = aiohttp.web.TCPSite(
				self.WebAppRunner,
				host=addr, port=port, backlog=self.BackLog,
				ssl_context=ssl_context,
			)
			try:
				await site.start()
			except OSError as err:
				L.error(
					"Web server failed to bind to the configured listen address.",
					struct_data={"address": addr, "port": port, "error": str(err)},
				)

			if isinstance(site, aiohttp.web_runner.TCPSite):
				for address in site._runner.addresses:
					if self.Addresses is None:
						self.Addresses = []
					self.Addresses.append(address)

		self.WebApp['app'].PubSub.publish("WebContainer.started!", self)


	async def _stop(self, app: Application):
		self.WebApp['app'].PubSub.publish("WebContainer.stopped!", self)
		await self.WebAppRunner.cleanup()


	def enable_cors(
		self,
		allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
		preflight_paths: typing.Union[str, typing.Iterable[str], None] = None,
		allow_headers: typing.Union[str, typing.Iterable[str], None] = None,
		allow_methods: typing.Union[str, typing.Iterable[str], None] = None,
		allow_credentials: typing.Optional[bool] = None,
	):
		"""
		Enable Cross-Origin Resource Sharing on this web container.

		If `[web] cors` is non-empty, this method is called automatically during container
		construction. Applications such as SeaCat Auth can call it from code instead
		(leave `cors` empty and pass a callable origin check).

		Calling this method again replaces the origin policy and adds any new preflight
		paths. OPTIONS routes that are already registered are not added twice.

		Args:
			allow_origin: `"*"` to allow every origin, a string or iterable of allowed
				origins, or a callable `origin: str -> bool` for a dynamic allowlist.
			preflight_paths: Path prefixes (`/foo/*`) and exact paths that receive CORS
				headers, including OPTIONS preflight. Defaults to `[web] cors_preflight_paths`.
			allow_headers: Allowed request headers. Defaults to `[web] cors_allow_headers`.
			allow_methods: Allowed HTTP methods. Defaults to `[web] cors_allow_methods`.
			allow_credentials: Whether browsers may send cookies and Authorization.
				Defaults to `[web] cors_allow_credentials`. When this is true, the
				response echoes the request `Origin` even if `allow_origin` is `"*"`;
				`Access-Control-Allow-Origin: *` is never combined with credentials.
		"""
		if preflight_paths is None:
			preflight_paths = self.Config.get("cors_preflight_paths")
		if allow_headers is None:
			allow_headers = self.Config.get("cors_allow_headers")
		if allow_methods is None:
			allow_methods = self.Config.get("cors_allow_methods")
		if allow_credentials is None:
			allow_credentials = self.Config.getboolean("cors_allow_credentials")

		if self.CORSHandler is None:
			self.CORSHandler = cors.CORSHandler(
				allow_origin=allow_origin,
				paths=preflight_paths,
				allow_headers=allow_headers,
				allow_methods=allow_methods,
				allow_credentials=allow_credentials,
			)
		else:
			self.CORSHandler.set_policy(
				allow_origin,
				allow_headers,
				allow_methods,
				allow_credentials,
			)
			self.CORSHandler.add_paths(preflight_paths)

		self._register_preflight_routes(preflight_paths)


	def add_preflight_handlers(self, preflight_paths: typing.Iterable[str]):
		"""
		Add OPTIONS handlers and CORS path patterns to already-enabled CORS.

		Use `enable_cors()` to start CORS. This method only extends the set of paths.

		Args:
			preflight_paths: Path prefixes (`/foo/*`) and exact paths that should
				receive CORS, including OPTIONS preflight.
		"""
		if self.CORSHandler is None:
			raise RuntimeError("CORS is not enabled; call enable_cors() first.")
		self.CORSHandler.add_paths(preflight_paths)
		self._register_preflight_routes(preflight_paths)


	def _register_preflight_routes(self, preflight_paths: typing.Union[str, typing.Iterable[str], None]):
		for path in cors.normalize_path_list(preflight_paths):
			route_path = cors.path_to_route(path)
			if route_path in self._CORSPreflightRoutes:
				continue
			self.WebApp.router.add_route("OPTIONS", route_path, self._preflight_handler)
			self._CORSPreflightRoutes.add(route_path)


	async def _preflight_handler(self, request):
		# CORS headers are applied in `_on_prepare_response` so preflight and actual
		# responses share the same policy. 204 is returned even when Origin is omitted
		# or not allowed; in that case no CORS headers are sent.
		return aiohttp.web.HTTPNoContent()


	async def _on_prepare_response(self, request, response):
		response.headers['Server'] = self.ServerTokens

		if self.CORSHandler is not None:
			self.CORSHandler.apply(request, response)


	def get_ports(self) -> typing.List[str]:
		"""
		Return list of available ports.

		Returns:
			(list[str]) List of ports.
		"""
		ports = []
		for addr, port, ssl_context in self._listen:
			ports.append(port)
		return ports


@aiohttp.web.middleware
async def set_request_context(request: aiohttp.web.Request, handler):
	"""
	Make sure that the incoming aiohttp.web.Request is available via Request context variable
	"""
	request_ctx = Request.set(request)
	try:
		return await handler(request)
	finally:
		Request.reset(request_ctx)
