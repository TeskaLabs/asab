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

		# Make sure that the proactor service exists
		from ..proactor import Module
		app.add_module(Module)
		self.ProactorService = app.get_service("asab.ProactorService")

		self.Containers = []



	async def finalize(self, app):
		# Remove containers from the list
		while len(self.Containers) > 0:
			container = self.Containers.pop()
			await container._stop(app)



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
