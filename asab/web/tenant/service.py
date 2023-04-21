import re
import logging

import aiohttp

from ...abc.service import Service
from ...config import Config

#

L = logging.getLogger(__name__)

#


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
		self.TenantsTrusted = Config.getboolean("tenants", "trusted")
		self.Tenants = set()

		# Load tenants from configuration
		for tenant_id in re.split(r"[,\s]+", Config.get("tenants", "ids"), flags=re.MULTILINE):
			tenant_id = tenant_id.strip()
			# Skip comments and empty lines
			if len(tenant_id) == 0:
				continue
			if tenant_id[0] == '#':
				continue
			if tenant_id[0] == ';':
				continue
			self.Tenants.add(tenant_id)

		# Load tenants from URL
		self.TenantUrl = Config.get("tenants", "tenant_url")


	async def initialize(self, app):
		if len(self.TenantUrl) > 0:
			await self._update_tenants()
			# TODO: Websocket persistent API should be added to seacat auth to feed these changes in realtime (eventually)
			app.PubSub.subscribe("Application.tick/300!", self._update_tenants)


	def locate_tenant(self, tenant_id):
		if tenant_id in self.Tenants:
			return tenant_id
		elif self.TenantsTrusted:
			self.Tenants.add(tenant_id)
			return tenant_id
		else:
			return None


	def get_tenant_ids(self):
		# TODO: REMOVE?
		return self.get_tenants()


	def get_tenants(self):
		return list(self.Tenants)


	def add_web_api(self, web_container):
		from .web import TenantWebHandler
		self.TenantWebHandler = TenantWebHandler(self.App, self, web_container)


	async def _update_tenants(self, message_name=None):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.TenantUrl) as resp:
				if resp.status == 200:
					tenants_list = await resp.json()
					for tenant in tenants_list:
						if isinstance(tenant, str):
							self.Tenants.add(tenant)
						elif isinstance(tenant, dict) and "_id" in tenant:
							# TODO: REMOVE?
							self.Tenants.add(tenant["_id"])
						else:
							L.warning("Unknown tenant format: {}".format(tenant))
