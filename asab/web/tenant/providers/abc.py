import abc
import typing


class TenantProviderABC(abc.ABC):
	def __init__(self, app, config):
		self.App = app
		self.Config = config
		self.Tenants: typing.Set[str] = set()

	async def initialize(self, app):
		pass
