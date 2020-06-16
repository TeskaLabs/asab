import asyncio

from ..abc.service import Service
from ..config import Config

from .container import ZooKeeperContainer


class ZooKeeperService(Service):
	"""
	ZooKeeperService connects to Zookeeper via aiozk client:
	https://zookeeper.apache.org/
	https://pypi.org/project/aiozk/
	"""

	Config.add_defaults({
		"zookeeper": {  # create a default container, also ensures backward compatibility
			"urls": "",  # zookeeper:12181
			"path": "",  # /asab
		}
	})

	def __init__(self, app, service_name, config_section="zookeeper"):
		super().__init__(app, service_name)
		self.App = app
		self.DefaultContainer = None
		self.Containers = {}
		self.Futures = []

	async def initialize(self, app):
		# Create a default container
		# Default container ensures backward compatibility
		urls = Config["zookeeper"]["urls"]
		if len(urls) > 0:
			self.DefaultContainer = ZooKeeperContainer(app, "zookeeper")
			await self.DefaultContainer.initialize(app)

	async def finalize(self, app):
		if len(self.Futures) > 0:
			await asyncio.wait(self.Futures)
		if self.DefaultContainer is not None:
			await self.DefaultContainer.finalize(app)
		for containers in self.Containers.values():
			await containers.finalize(app)

	def register_container(self, container):
		self.Containers[container.ConfigSectionName] = container
		self.Futures.append(asyncio.ensure_future(container.initialize(self.App)))

	async def advertise(self, data, encoding="utf-8", container=None):
		if container is None:
			container = self.DefaultContainer
		if container is None:
			raise RuntimeError("The container must be specified.")
		return await container.advertise(data, encoding)

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
