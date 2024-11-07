import re

from .abc import TenantProviderABC


class StaticTenantProvider(TenantProviderABC):
	def __init__(self, app, config):
		super().__init__(app, config)
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
			self.App.PubSub.publish("Tenants.change!")
