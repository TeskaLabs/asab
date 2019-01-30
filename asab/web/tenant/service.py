import asab
from .tenant import Tenant

asab.Config.add_defaults({
	'tenants': {
		'ids': '',
	}
})


class TenantService(asab.Service):

	def __init__(self, app, service_name="tenant_service"):
		super().__init__(app, service_name)
		self.Tenants = {}
		tenant_ids = asab.Config['tenants']['ids']
		tenant_ids = tenant_ids.split(',')

		for tenant_id in tenant_ids:
			self.Tenants[tenant_id] = Tenant(tenant_id)

	def locate_tenant(self, tenant_id):
		return self.Tenants.get(tenant_id)
