import abc
import typing


class TenantProviderABC(abc.ABC):
	def __init__(self, app, config):
		self.App = app
		self.Config = config

	async def initialize(self, app):
		pass

	def get_tenants(self) -> typing.Set[str]:
		return set()

	def is_tenant_known(self, tenant: str) -> bool:
		return False
