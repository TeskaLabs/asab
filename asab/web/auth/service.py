import functools
import inspect
import logging
import typing

import aiohttp
import aiohttp.web
import aiohttp.client_exceptions

try:
	import jwcrypto.jwk
	import jwcrypto.jwt
	import jwcrypto.jws
except ModuleNotFoundError:
	jwcrypto = None

from ... import LogObsolete
from ...abc.service import Service
from ...config import Config
from ...exceptions import NotAuthenticatedError
from ...utils import string_to_boolean
from ...contextvars import Tenant, Authz
from .authorization import Authorization


L = logging.getLogger(__name__)


class AuthService(Service):
	"""
	Provides authentication and authorization of incoming requests.
	"""

	def __init__(self, app, service_name="asab.AuthService"):
		super().__init__(app, service_name)

		if jwcrypto is None:
			raise ModuleNotFoundError(
				"You are trying to use asab.web.auth module without 'jwcrypto' installed. "
				"Please run 'pip install jwcrypto' "
				"or install asab with 'authz' optional dependency."
			)

		self.DiscoveryService = self.App.get_service("asab.DiscoveryService")
		self.Providers: list = []
		self._set_up_providers()

		# Try to auto-install authorization middleware
		self._try_auto_install()


	def get_provider(self, provider_type: str):
		for provider in self.Providers:
			if provider.Type == provider_type:
				return provider
		return None


	def get_authorized_tenant(self, request=None) -> typing.Optional[str]:
		"""
		DEPRECATED. Get the request's authorized tenant.
		"""
		authz = Authz.get()
		resources = authz.get_claim("resources", {})
		for tenant in resources.keys():
			if tenant == "*":
				continue
			# Return the first authorized tenant
			return tenant

		return None


	async def initialize(self, app):
		self._validate_wrapper_installation()


	def is_enabled(self) -> bool:
		"""
		OBSOLETE. Check if the AuthService is enabled. Mock mode counts as enabled too.
		"""
		LogObsolete.warning(
			"AuthService.is_enabled() is obsolete since it is not possible to disable AuthService anymore.",
			struct_data={"eol": "2025-03-31"}
		)
		return True


	def install(self, web_container):
		"""
		Apply authorization to all web handlers in a web container.

		:param web_container: Web container to be protected by authorization.
		:type web_container: asab.web.WebContainer
		"""
		web_service = self.App.get_service("asab.WebService")

		# Check that the middleware has not been installed yet
		if self.set_up_auth_web_wrapper in web_container.WebApp.on_startup:
			if len(web_service.Containers) == 1:
				raise RuntimeError(
					"WebContainer has authorization middleware installed already. "
					"You don't need to call `AuthService.install()` in applications with a single WebContainer; "
					"it is called automatically at init time."
				)
			else:
				raise RuntimeError("WebContainer has authorization middleware installed already.")

		tenant_service = self.App.get_service("asab.TenantService")
		if tenant_service is None:
			web_container.WebApp.on_startup.append(self.set_up_auth_web_wrapper)
			return

		tenant_wrapper_idx = tenant_service.get_web_wrapper_position(web_container)
		if tenant_wrapper_idx is not None:
			# Tenant wrapper is present - Auth wrapper must be applied before it
			web_container.WebApp.on_startup.insert(tenant_wrapper_idx, self.set_up_auth_web_wrapper)
		else:
			web_container.WebApp.on_startup.append(self.set_up_auth_web_wrapper)


	async def authorize_request(self, request: aiohttp.web.Request) -> Authorization:
		"""
		Authenticate and authorize request with first valid provider

		Args:
			request (aiohttp.web.Request): Request to authenticate and authorize

		Returns:
			Authorization object

		Raises:
			NotAuthenticatedError: When no provider is able to authorize the request
		"""
		for provider in self.Providers:
			try:
				return await provider.authorize(request)
			except NotAuthenticatedError:
				# Provider was unable to authenticate request
				# L.debug("Authorization failed.", struct_data={"auth_provider": provider.Type})
				pass

		L.warning("Cannot authenticate request: No valid authorization provider found.")
		raise NotAuthenticatedError()


	def _set_up_providers(self):
		# Always set up an ID token provider without public keys
		# The public keys are set up based on app configuration or added later
		from .providers import IdTokenAuthProvider
		id_token_provider = IdTokenAuthProvider(self.App)
		self.Providers.append(id_token_provider)

		public_keys_url = Config.get("auth", "public_keys_url") or None
		if public_keys_url:
			from .providers.key_providers import UrlPublicKeyProvider
			public_key_provider = UrlPublicKeyProvider(self.App, public_keys_url)
			id_token_provider.register_key_provider(public_key_provider)
		else:
			public_key_provider = None

		enabled = Config.get("auth", "enabled", fallback="production")
		try:
			enabled = string_to_boolean(enabled)
		except ValueError:
			pass

		if enabled == "production" or enabled is True:
			# Production mode is enabled by default
			# The ID token provider is already set up
			return

		elif enabled == "development":
			introspection_url = Config.get("auth", "introspection_url", fallback=None)
			if introspection_url is None or public_key_provider is None:
				raise ValueError(
					"AuthService is in development mode, but introspection_url or public_keys_url is not set."
				)

			L.warning(
				"AuthService is in development mode. "
				"Web requests will be authorized with introspection call to {}.".format(introspection_url)
			)
			from .providers import AccessTokenAuthProvider
			provider = AccessTokenAuthProvider(self.App, introspection_url=introspection_url)
			provider.register_key_provider(public_key_provider)
			self.Providers.append(provider)

		elif enabled == "mock":
			from .providers import MockAuthProvider
			auth_claims_path = (
				Config.get("auth", "mock_claims_path", fallback=None)
				or Config.get("auth", "mock_user_info_path", fallback=None)
			)
			provider = MockAuthProvider(self.App, auth_claims_path=auth_claims_path)
			# Make sure the mock provider is the first one and catches every request
			self.Providers.insert(0, provider)
			return

		elif enabled is False:
			raise ValueError("Disabling AuthService is deprecated. Use mock mode instead.")

		else:
			raise ValueError("Unsupported auth mode: {!r}".format(enabled))


	def _authorize_handler(self, handler):
		"""
		Authenticate the request by the JWT ID token in the Authorization header.
		Extract the token claims into Authorization context so that they can be used for authorization checks.
		"""
		@functools.wraps(handler)
		async def _authorize_handler_wrapper(*args, **kwargs):
			request = args[-1]

			# Authenticate and authorize request with first valid provider
			authz = await self.authorize_request(request)

			# Authorize tenant context
			tenant = Tenant.get(None)
			if tenant is not None:
				authz.require_tenant_access()

			authz_ctx = Authz.set(authz)
			try:
				return await handler(*args, **kwargs)
			finally:
				Authz.reset(authz_ctx)

		return _authorize_handler_wrapper


	async def set_up_auth_web_wrapper(self, aiohttp_app: aiohttp.web.Application):
		"""
		Inspect all registered handlers and wrap them in decorators according to their parameters.
		"""
		for route in aiohttp_app.router.routes():
			# Skip non-coroutines
			if not inspect.iscoroutinefunction(route.handler):
				continue

			# Skip OPTIONS routes, they should require no authentication
			if route.method == "OPTIONS":
				continue

			try:
				self._set_handler_auth(route)
			except Exception as e:
				raise Exception("Failed to initialize auth for handler {!r}.".format(route.handler.__qualname__)) from e


	def _set_handler_auth(self, route: aiohttp.web.AbstractRoute):
		"""
		Inspect handler and apply suitable auth wrappers.
		"""
		# Extract the actual unwrapped handler method for signature inspection
		handler_method = route.handler

		# Exclude endpoints with @noauth decorator
		if hasattr(handler_method, "NoAuth") and handler_method.NoAuth is True:
			return

		while hasattr(handler_method, "__wrapped__"):
			# While loop unwraps handlers wrapped in multiple decorators.
			# NOTE: This requires all the decorators to use @functools.wraps().
			handler_method = handler_method.__wrapped__

		if hasattr(handler_method, "__func__"):
			handler_method = handler_method.__func__

		argspec = inspect.getfullargspec(handler_method)
		args = set(argspec.kwonlyargs).union(argspec.args)

		# Extract the whole handler including its existing decorators and wrappers
		handler = route.handler

		# Apply the decorators IN REVERSE ORDER (the last applied wrapper affects the request first)

		# 2) Pass authorization attributes to handler method
		if "resources" in args:
			LogObsolete.warning(
				"The 'resources' argument is deprecated. "
				"Use the access-checking methods of asab.contextvars.Authz instead.",
				struct_data={"handler": handler.__qualname__, "eol": "2025-03-01"},
			)
			handler = _pass_resources(handler)

		if "user_info" in args:
			LogObsolete.warning(
				"The 'user_info' argument is deprecated. "
				"Use the Authorization object in asab.contextvars.Authz instead.",
				struct_data={"handler": handler.__qualname__, "eol": "2025-03-01"},
			)
			handler = _pass_user_info(handler)

		# 1) Authenticate and authorize request, authorize tenant from context, set Authorization context
		handler = self._authorize_handler(handler)

		route._handler = handler


	def _validate_wrapper_installation(self):
		"""
		Check if there is at least one web container with authorization installed
		"""
		web_service = self.App.get_service("asab.WebService")
		if web_service is None or len(web_service.Containers) == 0:
			L.warning("Authorization is not installed: There are no web containers.")
			return

		tenant_service = self.App.get_service("asab.TenantService")

		auth_wrapper_installed = False
		for web_container in web_service.Containers.values():
			try:
				auth_wrapper_idx = web_container.WebApp.on_startup.index(self.set_up_auth_web_wrapper)
				auth_wrapper_installed = True
			except ValueError:
				# Authorization wrapper not installed here
				continue

			if tenant_service is None:
				# Without tenant service there are no tenant web wrappers
				continue

			# Ensure the wrappers are applied in the correct order
			tenant_wrapper_idx = tenant_service.get_web_wrapper_position(web_container)
			if tenant_wrapper_idx is not None and auth_wrapper_idx > tenant_wrapper_idx:
				L.error(
					"TenantService.install(web_container) must be called before AuthService.install(web_container). "
					"Otherwise authorization will not work properly."
				)

		if not auth_wrapper_installed:
			L.warning(
				"Authorization is not installed in any web container. "
				"In applications with more than one WebContainer there is no automatic installation; "
				"you have to call `AuthService.install(web_container)` explicitly."
			)
			return


	def _try_auto_install(self):
		"""
		If there is exactly one web container, install authorization wrapper on it.
		"""
		web_service = self.App.get_service("asab.WebService")
		if web_service is None:
			return
		if len(web_service.Containers) != 1:
			return
		web_container = web_service.WebContainer

		self.install(web_container)
		L.debug("WebContainer authorization wrapper will be installed automatically.")


def _pass_user_info(handler):
	"""
	Add user info to the handler arguments
	"""
	@functools.wraps(handler)
	async def _pass_user_info_wrapper(*args, **kwargs):
		authz = Authz.get(None)
		return await handler(*args, user_info=authz.user_info() if authz is not None else None, **kwargs)
	return _pass_user_info_wrapper


def _pass_resources(handler):
	"""
	Add resources to the handler arguments
	"""
	@functools.wraps(handler)
	async def _pass_resources_wrapper(*args, **kwargs):
		authz = Authz.get(None)
		return await handler(*args, resources=authz._resources() if authz is not None else None, **kwargs)
	return _pass_resources_wrapper
