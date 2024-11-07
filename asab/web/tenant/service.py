import logging
import typing

from ...abc.service import Service
from ...config import Config

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

		self._prepare_providers()


	def _prepare_providers(self):
		if Config.get("tenants", "ids"):
			from .providers import StaticTenantProvider
			self.Providers.add(StaticTenantProvider(self.App, Config["tenants"]))

		if Config.get("tenants", "tenant_url"):
			from .providers import WebTenantProvider
			self.Providers.add(WebTenantProvider(self.App, Config["tenants"]))


	async def initialize(self, app):
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

	def locate_tenant(self, tenant_id):
		if tenant_id in self.Tenants:
			return tenant_id
		elif self.TenantsTrusted:
			self.Tenants.add(tenant_id)
			return tenant_id
		else:
			return None


	def get_tenants(self):
		return list(self.Tenants)


	def add_web_api(self, web_container):
		from .web import TenantWebHandler
		self.TenantWebHandler = TenantWebHandler(self.App, self, web_container)


	async def _update_tenants(self, message_name=None):
		new_tenants = set()

		if len(self.TenantUrl) > 0:
			async with aiohttp.ClientSession() as session:
				async with session.get(self.TenantUrl) as resp:
					if resp.status == 200:
						external_tenants = await resp.json()
					else:
						L.warning("Failed to load tenants.", struct_data={"url": self.TenantUrl})
						return

			new_tenants.update(external_tenants)

		if len(self._StaticTenants) > 0:
			new_tenants.update(self._StaticTenants)

		if self.Tenants != new_tenants:
			self.App.PubSub.publish("Tenants.change!")
			self.Tenants = new_tenants


def _read_tenants_from_config() -> typing.Set[str]:
	tenants = set()
	for tenant_id in re.split(r"[,\s]+", Config.get("tenants", "ids"), flags=re.MULTILINE):
		tenant_id = tenant_id.strip()
		# Skip comments and empty lines
		if len(tenant_id) == 0:
			continue
		if tenant_id[0] == '#':
			continue
		if tenant_id[0] == ';':
			continue
		tenants.add(tenant_id)
	return tenants
