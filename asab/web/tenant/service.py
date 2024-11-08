import logging
import typing

from ...abc.service import Service
from ...config import Config
from .middleware import set_up_tenant_context

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

	def __init__(self, app, service_name="asab.TenantService"):
		super().__init__(app, service_name)
		self.App = app
		self.Providers = set()

		auth_svc = self.App.get_service("asab.AuthService")
		if auth_svc is not None:
			raise Exception("Please initialize TenantService BEFORE AuthService.")

		self._prepare_providers()
		self._try_auto_install()


	def _prepare_providers(self):
		if Config.get("tenants", "ids", fallback=None):
			from .providers import StaticTenantProvider
			self.Providers.add(StaticTenantProvider(self.App, Config["tenants"]))

		if Config.get("tenants", "tenant_url", fallback=None):
			from .providers import WebTenantProvider
			self.Providers.add(WebTenantProvider(self.App, Config["tenants"]))


	async def initialize(self, app):
		self._check_if_installed()
		for provider in self.Providers:
			await provider.initialize(app)


	@property
	def Tenants(self) -> typing.Set[str]:
		tenants = set()
		for provider in self.Providers:
			tenants.update(provider.Tenants)

		return tenants


	def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants


	def install(self, web_container):
		"""
		Apply tenant context to all web handlers in a web container.

		Args:
			web_container: Web container to add tenant context to.
		"""
		web_service = self.App.get_service("asab.WebService")

		# Check that the middleware has not been installed yet
		for middleware in web_container.WebApp.on_startup:
			if middleware == set_up_tenant_context:
				if len(web_service.Containers) == 1:
					L.warning(
						"WebContainer has tenant middleware installed already. "
						"You don't need to call `TenantService.install()` in applications with a single WebContainer; "
						"it is called automatically at init time."
					)
				else:
					L.warning("WebContainer has tenant middleware installed already.")
				return

		web_container.WebApp.on_startup.append(set_up_tenant_context)


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
		L.info("WebContainer tenant context installed automatically.")


	def _check_if_installed(self):
		"""
		Check if there is at least one web container with tenant middleware installed
		"""
		web_service = self.App.get_service("asab.WebService")
		if web_service is None or len(web_service.Containers) == 0:
			L.warning("Tenant middleware is not installed: There are no web containers.")
			return

		for web_container in web_service.Containers.values():
			for middleware in web_container.WebApp.on_startup:
				if middleware == set_up_tenant_context:
					# Container has tenant middleware installed
					break
			else:
				continue

			# Container has tenant middleware installed
			break

		else:
			L.warning(
				"Tenant middleware is not installed in any web container. "
				"In applications with more than one WebContainer there is no automatic installation; "
				"you have to call `TenantService.install(web_container)` explicitly."
			)
			return
