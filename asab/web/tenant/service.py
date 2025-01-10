import asyncio
import typing
import inspect
import logging

import aiohttp.web

from ... import LOG_NOTICE
from ...abc.service import Service
from ...config import Config
from .utils import set_handler_tenant
from .providers.abc import TenantProviderABC

#

L = logging.getLogger(__name__)

#


class TenantService(Service):
	"""
	Provides set of known tenants and tenant extraction for web requests.
	"""

	def __init__(self, app, service_name: str = "asab.TenantService", auto_install_web_wrapper: bool = True):
		"""
		Initialize and register a new TenantService.

		Args:
			app: ASAB application.
			service_name: ASAB service identifier.
			auto_install_web_wrapper: Whether to automatically install tenant context wrapper to WebContainer.
		"""
		super().__init__(app, service_name)
		auth_svc = self.App.get_service("asab.AuthService")
		if auth_svc is not None:
			raise RuntimeError("Please initialize TenantService before AuthService.")

		self.Providers: typing.List[TenantProviderABC] = []  # Must be a list to be deterministic
		self._prepare_providers()

		if auto_install_web_wrapper:
			self._try_auto_install()

		self.App.PubSub.subscribe("Application.tick/300!", self._every_five_minutes)


	async def initialize(self, app):
		if len(self.Providers) == 0:
			L.error(
				"TenantService requires at least one provider. "
				"Specify either `tenant_url` or `ids` in the [tenants] config section."
			)

		await self.update_tenants()


	@property
	def Tenants(self) -> typing.Set[str]:
		"""
		DEPRECATED. Get the set of known tenant IDs.

		.. deprecated:: 25.01
			Use coroutine `get_tenants()` instead.
		"""
		raise AttributeError("Property `Tenants` has been removed. Use coroutine `get_tenants()` instead.")


	def _prepare_providers(self):
		if Config.get("tenants", "ids", fallback=None):
			from .providers import StaticTenantProvider
			self.Providers.append(StaticTenantProvider(self.App, self, Config["tenants"]))

		if Config.get("tenants", "tenant_url", fallback=None):
			from .providers import WebTenantProvider
			self.Providers.append(WebTenantProvider(self.App, self, Config["tenants"]))

		if Config.get("tenants", "zk_path", fallback=None):
			from .providers import ZookeeperTenantProvider
			self.Providers.append(ZookeeperTenantProvider(self.App, self, Config["tenants"]))


	async def _every_five_minutes(self, message_type=None):
		await self.update_tenants()


	async def update_tenants(self):
		"""
		Update all tenant providers.
		"""
		tasks = [provider.update() for provider in self.Providers]
		await asyncio.gather(*tasks)


	async def get_tenants(self) -> typing.Set[str]:
		"""
		Get the set of known tenant IDs.

		Returns:
			The set of known tenant IDs.
		"""
		await self.update_tenants()
		tenants = set()
		for provider in self.Providers:
			tenants |= await provider.get_tenants()

		return tenants


	async def is_tenant_known(self, tenant: str) -> bool:
		"""
		Check if the tenant is among known tenants.

		Args:
			tenant: Tenant ID to check.

		Returns:
			Whether the tenant is known.
		"""
		if tenant is None:
			return False
		if len(self.Providers) == 0:
			L.warning("No tenant provider registered.")
			return False
		for provider in self.Providers:
			if await provider.is_tenant_known(tenant):
				return True

		# Tenant not found; try to update tenants and try again
		await self.update_tenants()
		for provider in self.Providers:
			if await provider.is_tenant_known(tenant):
				return True

		return False


	def install(self, web_container):
		"""
		Apply tenant context wrappers to all web handlers in the web container.

		Args:
			web_container: Web container to add tenant context to.
		"""
		web_service = self.App.get_service("asab.WebService")

		# Check that the middleware has not been installed yet
		for middleware in web_container.WebApp.on_startup:
			if middleware == self._set_up_tenant_web_wrapper:
				if len(web_service.Containers) == 1:
					raise RuntimeError(
						"WebContainer has tenant middleware installed already. "
						"You don't need to call `TenantService.install()` in applications with a single WebContainer; "
						"it is called automatically at init time."
					)
				else:
					raise RuntimeError("WebContainer has tenant middleware installed already.")

		web_container.WebApp.on_startup.append(self._set_up_tenant_web_wrapper)


	def is_ready(self) -> bool:
		"""
		Check if all tenant providers are ready.

		Returns:
			bool: Are all tenant providers ready?
		"""
		for provider in self.Providers:
			if not provider.is_ready():
				return False
		return True


	def set_ready(self, provider: TenantProviderABC):
		"""
		Update tenant service ready status.

		Args:
			provider: Tenant provider that updated its ready status.
		"""
		if len(self.Providers) == 0:
			return

		if self.is_ready():
			L.log(LOG_NOTICE, "is ready.")
			self.App.PubSub.publish("Tenants.ready!", self)
		elif not provider.is_ready():
			L.log(LOG_NOTICE, "is NOT ready.")
			self.App.PubSub.publish("Tenants.not_ready!", self)


	def get_web_wrapper_position(self, web_container) -> typing.Optional[int]:
		"""
		Check if tenant web wrapper is installed in container and where.

		Args:
			web_container: Web container to inspect.

		Returns:
			typing.Optional[int]: The index at which the wrapper is located, or `None` if it is not installed.
		"""
		try:
			return web_container.WebApp.on_startup.index(self._set_up_tenant_web_wrapper)
		except ValueError:
			return None


	def _try_auto_install(self):
		"""
		If there is exactly one web container, install tenant middleware on it.
		"""
		web_service = self.App.get_service("asab.WebService")
		if web_service is None:
			return
		if len(web_service.Containers) != 1:
			return
		web_container = web_service.WebContainer

		self.install(web_container)
		L.debug("WebContainer tenant wrapper will be installed automatically.")


	async def _set_up_tenant_web_wrapper(self, aiohttp_app: aiohttp.web.Application):
		"""
		Inspect all registered handlers and wrap them in decorators according to their parameters.
		"""
		for route in aiohttp_app.router.routes():
			# Skip non-coroutines
			if not inspect.iscoroutinefunction(route.handler):
				continue

			try:
				set_handler_tenant(self, route)
			except Exception as e:
				raise RuntimeError(
					"Failed to initialize tenant context for handler {!r}.".format(route.handler.__qualname__)
				) from e
