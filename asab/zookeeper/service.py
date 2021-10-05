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
		"asab:zookeeper": {
			# Server list to which ZooKeeper Client tries connecting.
			# Specify a comma (,) separated server list.
			# A server is defined as address:port format.
			# "servers": "zookeeper:12181",
			"servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181",
			"path": "/asab",
		}
	})

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.App = app
		self.Containers = {}
		self.Futures = []


	async def finalize(self, app):
		if len(self.Futures) > 0:
			await asyncio.wait(self.Futures)
		for containers in self.Containers.values():
			await containers.finalize(app)


	@property
	def DefaultContainer(self):
		'''
		This is here to maintain backward compatibility.
		'''
		container = self.Containers.get('asab:zookeeper')
		if container is None:
			container = self.build_container()
		return container


	def build_container(self, config_section_name="asab:zookeeper"):
		container = ZooKeeperContainer(self.App, config_section_name,z_path=None)
		self.Containers[container.ConfigSectionName] = container
		self.Futures.append(asyncio.ensure_future(
			container.initialize(self.App)
		))
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
