import re

import aiohttp

from ...abc.service import Service
from ...config import Config

from .tenant import Tenant

# "tenant_url" is used to periodically refresh tenants from, expecting "_id" inside a JSON structure,
# which is compatible with SeaCat Auth product
Config.add_defaults({
	'tenants': {
		'ids': '',  # List of tenant ids, entries can be separated by comma or newline
		'tenant_url': '',  # f. e. http://seacat-auth:8080/tenant
		'trusted': 0,  # makes sure the tenants are implicitly trusted, even though they are not located in IDs or tenant URL
	}
})


class TenantService(Service):

	def __init__(self, app, service_name="asab.TenantService"):
		super().__init__(app, service_name)
		self.App = app
		self.TenantWebHandler = None
		self.TenantsTrusted = int(Config['tenants']['trusted'])
		self.Tenants = {}

		# Load tenants from configuration
		for tenant_id in re.split(r"[,\s]+", Config['tenants']['ids'], flags=re.MULTILINE):
			tenant_id = tenant_id.strip()
			if len(tenant_id) == 0:
				continue
			if tenant_id[0] == '#':
				continue
			if tenant_id[0] == ';':
				continue

			section = 'tenant:params:{}'.format(tenant_id)
			if Config.has_section(section):
				params = dict(Config.items(section))
				self.Tenants[tenant_id] = Tenant(tenant_id, params)
			else:
				self.Tenants[tenant_id] = Tenant(tenant_id)

		# Load tenants from URL
		self.TenantUrl = Config["tenants"]["tenant_url"]


	async def initialize(self, app):
		if len(self.TenantUrl) > 0:
			await self._update_tenants()
			# TODO: Websocket persistent API should be added to seacat auth to feed these changes in realtime (eventually)
			app.PubSub.subscribe("Application.tick/300!", self._update_tenants)


	@property
	def TenantIds(self):
		'''
		This is here for a backward compatibility.
		Remove after Jan 2022
		'''
		L.warning("The TenantService.TenantIds is deprecated, use TenantService.get_tenant_ids()")
		return get_tenant_ids()


	def locate_tenant(self, tenant_id):
		tenant = self.Tenants.get(tenant_id)
		if tenant is None and self.TenantsTrusted > 0:
			tenant = {"_id": tenant_id}
			self.Tenants[tenant_id] = tenant
		return tenant


	def get_tenant_ids(self):
		return list(self.Tenants.keys())


	def get_tenants(self):
		tenants = []
		for tenant in self.Tenants.values():
			tenants.append(tenant.to_dict())
		return tenants


	def add_web_api(self, web_container):
		from .web import TenantWebHandler
		self.TenantWebHandler = TenantWebHandler(self.App, self, web_container)


	async def _update_tenants(self, message_name=None):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.TenantUrl) as resp:
				if resp.status == 200:
					tenants_list = await resp.json()
					for tenant in tenants_list:
						self.Tenants[tenant["_id"]] = tenant
