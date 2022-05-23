import logging
from ..abc.service import Service
from .. import Config
from .container import ZooKeeperContainer

#

L = logging.getLogger(__name__)

#


class ZooKeeperService(Service):

	ConfigSectionAliases = ["asab:zookeeper"]

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.App = app
		self.Containers = {}


	async def finalize(self, app):
		for containers in self.Containers.values():
			await containers._stop(app)


	@property
	def DefaultContainer(self):
		'''
		This is here to maintain backward compatibility.
		'''
		config_section = 'zookeeper'

		# The WebContainer should be configured in the config section [web]
		if config_section not in Config.sections():
			# If there is no [web] section, try other aliases for backwards compatibility
			for alias in self.ConfigSectionAliases:
				if alias in Config.sections():
					config_section = alias
					L.warning("Using obsolete config section [{}]. Preferred section name is [zookeeper]. ".format(alias))
					break
			else:
				raise RuntimeError("No [zookeeper] section configured.")

		container = self.Containers.get(config_section)
		if container is None:
			container = ZooKeeperContainer(self, config_section_name=config_section)

		return container


	def _register_container(self, container):
		self.Containers[container.ConfigSectionName] = container
		container.ZooKeeper.ProactorService.schedule(container._start, self.App)


	async def advertise(self, data, path, encoding="utf-8", container=None):
		if container is None:
			container = self.DefaultContainer
		if container is None:
			raise RuntimeError("The container must be specified.")
		return await container.advertise(data, path, encoding)


	async def get_children(self, container=None):
		if container is None:
			container = self.DefaultContainer
		if container is None:
			raise RuntimeError("The container must be specified.")
		return await container.get_children()

	async def get_data(self, child, encoding="utf-8", container=None):
		if container is None:
			container = self.DefaultContainer
		if container is None:
			raise RuntimeError("The container must be specified.")
		return await container.get_data(child, encoding)

	async def get_raw_data(self, child, container=None):
		if container is None:
			container = self.DefaultContainer
		if container is None:
			raise RuntimeError("The container must be specified.")
		return await container.get_raw_data(child)
