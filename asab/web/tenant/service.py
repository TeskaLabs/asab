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
