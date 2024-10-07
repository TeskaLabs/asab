import re
import logging
import typing

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
		self.Tenants: typing.Set[str] = set()
		self._StaticTenants: typing.Set[str] = _read_tenants_from_config()

		# Load tenants from URL
		self.TenantUrl = Config.get("tenants", "tenant_url")
		if len(self.TenantUrl) > 0:
			app.PubSub.subscribe("Application.tick/10!", self._update_tenants)


	async def initialize(self, app):
		await self._update_tenants()


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
			self.App.PubSub.publish("Tenants.changed!")
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
