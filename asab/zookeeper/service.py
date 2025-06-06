import logging

from ..abc.service import Service

#

L = logging.getLogger(__name__)

#


class ZooKeeperService(Service):

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
			await self.remove(self.Containers[-1])


	async def remove(self, container):
		try:
			self.Containers.remove(container)
			await container._stop()
		except ValueError:
			L.warning("Zookeeper not found in the list, check your initialization/finalization order")
			return
