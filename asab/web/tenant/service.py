import logging
import typing

from ...abc.service import Service
from ...config import Config
from .utils import set_up_tenant_web_wrapper

#

L = logging.getLogger(__name__)

#


Config.add_defaults({
	"tenants": {
		# List of tenant IDs, entries can be separated by comma or newline
		"ids": "",

		# URL that provides a JSON array of tenant IDs
		"tenant_url": "",
	}
})


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
		self.App = app
		self.Providers = set()

		auth_svc = self.App.get_service("asab.AuthService")
		if auth_svc is not None:
			raise Exception("Please initialize TenantService BEFORE AuthService.")

		self._prepare_providers()
		if auto_install_web_wrapper:
			self._try_auto_install()


	def _prepare_providers(self):
		if Config.get("tenants", "ids", fallback=None):
			from .providers import StaticTenantProvider
			self.Providers.add(StaticTenantProvider(self.App, Config["tenants"]))

		if Config.get("tenants", "tenant_url", fallback=None):
			from .providers import WebTenantProvider
			self.Providers.add(WebTenantProvider(self.App, Config["tenants"]))


	async def initialize(self, app):
		for provider in self.Providers:
			await provider.initialize(app)


	@property
	def Tenants(self) -> typing.Set[str]:
		"""
		Get the set of known tenant IDs.

		Returns:
			The set of known tenant IDs.
		"""
		tenants = set()
		for provider in self.Providers:
			tenants.update(provider.Tenants)

		return tenants


	def get_tenants(self) -> typing.Set[str]:
		"""
		Get the set of known tenant IDs.

		Returns:
			The set of known tenant IDs.
		"""
		return self.Tenants


	def is_tenant_known(self, tenant: str) -> bool:
		"""
		Check if the tenant is among known tenants.

		Args:
			tenant: Tenant ID to check.

		Returns:
			Whether the tenant is known.
		"""
		return tenant in self.Tenants


	def install(self, web_container):
		"""
		Apply tenant context wrappers to all web handlers in the web container.

		Args:
			web_container: Web container to add tenant context to.
		"""
		web_service = self.App.get_service("asab.WebService")

		# Check that the middleware has not been installed yet
		for middleware in web_container.WebApp.on_startup:
			if middleware == set_up_tenant_web_wrapper:
				if len(web_service.Containers) == 1:
					raise Exception(
						"WebContainer has tenant middleware installed already. "
						"You don't need to call `TenantService.install()` in applications with a single WebContainer; "
						"it is called automatically at init time."
					)
				else:
					raise Exception("WebContainer has tenant middleware installed already.")

		web_container.WebApp.on_startup.append(set_up_tenant_web_wrapper)


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
		L.info("WebContainer tenant context wrapper will be installed automatically.")
