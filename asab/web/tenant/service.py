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

			section = 'tenant:params:{}'.format(tenant_id)

			if asab.Config.has_section(section):
				params = dict(asab.Config.items(section))
				self.Tenants[tenant_id] = Tenant(tenant_id, params)
			else:
				self.Tenants[tenant_id] = Tenant(tenant_id)

	def locate_tenant(self, tenant_id):
		return self.Tenants.get(tenant_id)

	def get_tenants(self):

		tenants = []

		for tenant in self.Tenants.values():
			tenants.append(tenant.to_dict())

		return tenants

	def add_web_api(self, web_container):

		from .web import TenantWebHandler
		self.TenantWebHandler = TenantWebHandler(self.App, self, web_container)
