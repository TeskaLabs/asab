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
		"asab:zookeeper": {  # create a default container, also ensures backward compatibility
			"servers": "",  # zookeeper:12181
			"path": "",  # /asab
		}
	})

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.App = app
		self.DefaultContainer = None
		self.Containers = {}
		self.Futures = []


	async def initialize(self, app):
		# Create a default container
		# Default container ensures backward compatibility
		servers = Config["asab:zookeeper"]["servers"]
		if len(servers) > 0:
			self.DefaultContainer = ZooKeeperContainer(app, "asab:zookeeper")
			await self.DefaultContainer.initialize(app)

	async def finalize(self, app):
		if len(self.Futures) > 0:
			await asyncio.wait(self.Futures)
		if self.DefaultContainer is not None:
			await self.DefaultContainer.finalize(app)
		for containers in self.Containers.values():
			await containers.finalize(app)

	def build_container(self):
		container = ZooKeeperContainer(self.App, "asab:zookeeper")
		self.Containers[container.ConfigSectionName] = container
		self.Futures.append(asyncio.ensure_future(container.initialize(self.App)))
		return container

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
