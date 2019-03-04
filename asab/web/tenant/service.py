import asab
from .tenant import Tenant

asab.Config.add_defaults({
	'tenants': {
		'ids': '',
	}
})


class TenantService(asab.Service):

	def __init__(self, app, service_name="asab.TenantService"):
		super().__init__(app, service_name)
		self.App = app
		self.Tenants = {}
		self.TenantIds = asab.Config['tenants']['ids']
		self.TenantIds = self.TenantIds.split(',')

		for tenant_id in self.TenantIds:
			self.Tenants[tenant_id] = Tenant(tenant_id)

	def locate_tenant(self, tenant_id):
		return self.Tenants.get(tenant_id)

	def get_list_of_tenants(self):
		return self.TenantIds

	def add_web_api(self):

		from .web import TenantWebHandler
		self.TenantWebHandler = TenantWebHandler(self.App, self)
