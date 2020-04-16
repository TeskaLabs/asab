import aiohttp

from ...abc.service import Service
from ...config import Config

from .tenant import Tenant

Config.add_defaults({
	'tenants': {
		'ids': '',
		# URL to periodically refresh tenants from, expecting "_id" inside a JSON structure,
		# which is compatible with SeaCat Auth product
		'url': '',  # f. e. http://seacat-auth:8080/tenant
	}
})


class TenantService(Service):

	def __init__(self, app, service_name="asab.TenantService"):
		super().__init__(app, service_name)
		self.App = app
		self.TenantWebHandler = None
		self.Tenants = {}

		# Load tenants from configuration
		self.TenantIds = Config['tenants']['ids']
		self.TenantIds = self.TenantIds.split(',')
		for tenant_id in self.TenantIds:
			section = 'tenant:params:{}'.format(tenant_id)
			if Config.has_section(section):
				params = dict(Config.items(section))
				self.Tenants[tenant_id] = Tenant(tenant_id, params)
			else:
				self.Tenants[tenant_id] = Tenant(tenant_id)

		# Load tenants from URL
		self.TenantUrl = Config["tenants"]["url"]
		if len(self.TenantUrl) > 0:
			app.PubSub.subscribe("Application.tick/10!", self._update_tenants)

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

	async def _update_tenants(self, message_name):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.TenantUrl) as resp:
				if resp.status == 200:
					tenants_list = await resp.json()
					for tenant in tenants_list:
						self.Tenants[tenant["_id"]] = tenant
