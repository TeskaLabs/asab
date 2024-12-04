import re
import typing
import logging

from .abc import TenantProviderABC

L = logging.getLogger(__name__)


class StaticTenantProvider(TenantProviderABC):


	def __init__(self, app, tenant_service, config):
		super().__init__(app, tenant_service, config)
		self.Tenants: typing.Set[str] = set()
		self._read_tenants_from_config()


	def _read_tenants_from_config(self):
		for tenant_id in re.split(r"[,\s]+", self.Config.get("ids", ""), flags=re.MULTILINE):
			tenant_id = tenant_id.strip()
			# Skip comments and empty lines
			if len(tenant_id) == 0:
				continue
			if tenant_id[0] == "#":
				continue
			if tenant_id[0] == ";":
				continue
			self.Tenants.add(tenant_id)

		if len(self.Tenants) > 0:
			L.info("Static tenants loaded from config.")
			self.App.PubSub.publish("Tenants.change!")

		self._set_ready(True)


	def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants
