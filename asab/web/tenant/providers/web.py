import typing
import logging
import aiohttp

from .abc import TenantProviderABC


L = logging.getLogger(__name__)


class WebTenantProvider(TenantProviderABC):
	def __init__(self, app, config):
		super().__init__(app, config)
		self.Tenants: typing.Set[str] = set()

		self.TaskService = self.App.get_service("asab.TaskService")
		self.TenantUrl = self.Config.get("tenant_url")

		self.App.PubSub.subscribe("Application.tick/300!", self._every_five_minutes)


	async def initialize(self, app):
		self.TaskService.schedule(self._update_tenants())


	def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants


	async def _every_five_minutes(self, message_type=None):
		self.TaskService.schedule(self._update_tenants())


	async def _update_tenants(self, message_type=None):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.TenantUrl) as resp:
				if resp.status == 200:
					external_tenants = await resp.json()
				else:
					L.warning("Failed to load tenants.", struct_data={"url": self.TenantUrl})
					return

		new_tenants = set(external_tenants)
		if self.Tenants != new_tenants:
			self.Tenants = new_tenants
			self.App.PubSub.publish("Tenants.change!")
