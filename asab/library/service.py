import logging
import asab
from .providers import ZooKeeperLibraryProvider, FileSystemLibraryProvider
#

L = logging.getLogger(__name__)

#


class LibraryService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		app.PubSub.subscribe_all(self)

		provider = asab.Config["asab:library"]["provider"]
		if provider.startswith("zk://"):
			self.Provider = ZooKeeperLibraryProvider(self.App, self, provider)

		else:
			self.Provider = FileSystemLibraryProvider(self.App, self, provider)


	async def initialize(self, app):
		L.info("Sample service initialized.")
		await self.Provider.initialize()

	async def read(self, file):
		res = await self.Provider.read(file)
		return res

	async def finalize(self, app):
		L.info("Sample service finalized.")

	# @asab.subscribe("Application.tick!")
	# async def on_tick(self, message_type):
	# 	self.counter = self.counter + 1
	# 	L.info(message_type, struct_data={"counter": self.counter})
