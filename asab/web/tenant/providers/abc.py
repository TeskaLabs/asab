import abc
import typing


class TenantProviderABC(abc.ABC):
	def __init__(self, app, tenant_service, config):
		self.App = app
		self.TenantService = tenant_service
		self.Config = config
		self._IsReady = False

	async def update(self):
		pass

	async def get_tenants(self) -> typing.Set[str]:
		return set()

	async def is_tenant_known(self, tenant: str) -> bool:
		return False

	def is_ready(self) -> bool:
		return self._IsReady

	def _set_ready(self, ready: bool = True):
		self._IsReady = ready
		self.TenantService.check_ready()
