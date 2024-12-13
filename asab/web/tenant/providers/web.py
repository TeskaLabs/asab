import typing
import logging
import aiohttp
import aiohttp.client_exceptions

from .abc import TenantProviderABC


L = logging.getLogger(__name__)


class WebTenantProvider(TenantProviderABC):
	def __init__(self, app, tenant_service, config):
		super().__init__(app, tenant_service, config)
		self.Tenants: typing.Set[str] = set()

		self.DiscoveryService = self.App.get_service("asab.DiscoveryService")
		self.TenantUrl = self.Config.get("tenant_url")


	async def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	async def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants


	async def update(self):
		if self.DiscoveryService is not None:
			open_session = self.DiscoveryService.session
		else:
			open_session = aiohttp.ClientSession

		try:
			async with open_session() as session:
				async with session.get(self.TenantUrl) as resp:
					if resp.status == 200:
						external_tenants = await resp.json()
					elif 400 <= resp.status < 500:
						L.warning("Failed to load tenants: Client error.", struct_data={
							"url": self.TenantUrl,
							"status": resp.status,
							"reason": resp.reason,
						})
						self._set_ready(False)
						return
					else:
						L.warning("Failed to load tenants: Server error.", struct_data={
							"url": self.TenantUrl,
							"status": resp.status,
							"reason": resp.reason,
						})
						self._set_ready(False)
						return
		except aiohttp.client_exceptions.ClientConnectorError:
			L.warning("Failed to connect to tenant server.")
			self._set_ready(False)
			return

		new_tenants = set(external_tenants)
		if self.Tenants != new_tenants:
			L.debug("Tenants from URL updated.", struct_data={"url": self.TenantUrl})
			self.Tenants = new_tenants
			self.App.PubSub.publish("Tenants.change!")

		if not self._IsReady:
			self._set_ready(True)
