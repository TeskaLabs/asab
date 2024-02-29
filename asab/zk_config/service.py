import os

from ..abc import Service
from ..application import Application
from ..zookeeper.container import ZooKeeperContainer


from .zookeeper_provider import ZooKeeperProvider



class ConfigService(Service):
	def __init__(self, app: Application, zk_container: ZooKeeperContainer, service_name = "asab.ConfigService"):
		super().__init__(app, service_name)
		self.Provider = ZooKeeperProvider(app, zk_container=zk_container)

	async def finalize(self, app):
		await self.Provider.finalize(app)


	async def list_configs(self, config_type):
		return await self.Provider.list_configs(config_type)

	async def get_config(self, config_type, config_name):
		"""
		Only JSON format of the configuration is allowed. You can search by config name or the file name with the extension.
		Provider expects config types without extensions and config with extensions.
		"""
		_, node_extension = os.path.splitext(config_name)
		if node_extension == '':
			config_name = config_name + '.json'

		return await self.Provider.get_config(config_type, config_name)



	async def list_config_types(self):
		return await self.Provider.list_config_types()

	async def get_config_type(self, config_type):
		return await self.Provider.get_config_type(config_type)

