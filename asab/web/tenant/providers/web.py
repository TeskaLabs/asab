import typing
import logging
import aiohttp

from .abc import TenantProviderABC


L = logging.getLogger(__name__)


class WebTenantProvider(TenantProviderABC):
	def __init__(self, app, tenant_service, config):
		super().__init__(app, tenant_service, config)
		self.Tenants: typing.Set[str] = set()

		self.TaskService = self.App.get_service("asab.TaskService")
		self.DiscoveryService = self.App.get_service("asab.DiscoveryService")
		self.TenantUrl = self.Config.get("tenant_url")


	async def initialize(self, app):
		self.TaskService.schedule(self._update_tenants())


	async def update_tenants(self, asynchronously: bool = True):
		if asynchronously:
			self.TaskService.schedule(self._update_tenants())
		else:
			await self._update_tenants()


	def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants


	async def _update_tenants(self, message_type=None):
		if self.DiscoveryService is not None:
			open_session = self.DiscoveryService.session
		else:
			open_session = aiohttp.ClientSession

		async with open_session as session:
			async with session.get(self.TenantUrl) as resp:
				if resp.status == 200:
					external_tenants = await resp.json()
				else:
					L.warning("Failed to load tenants.", struct_data={"url": self.TenantUrl})
					self._set_ready(False)
					return

		new_tenants = set(external_tenants)
		if self.Tenants != new_tenants:
			L.debug("Tenants from URL updated.", struct_data={"url": self.TenantUrl})
			self.Tenants = new_tenants
			self.App.PubSub.publish("Tenants.change!")

		self._set_ready(True)
