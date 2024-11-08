import logging
import aiohttp

from .abc import TenantProviderABC


L = logging.getLogger(__name__)


class WebTenantProvider(TenantProviderABC):
	def __init__(self, app, config):
		super().__init__(app, config)
		self.TenantUrl = self.Config.get("tenant_url")

		self.App.PubSub.subscribe("Application.tick/300!", self._update_tenants)


	async def initialize(self, app):
		await self._update_tenants()


	async def _update_tenants(self, message_type=None):
		# TODO: Proactor service
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
