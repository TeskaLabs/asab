import logging
import asab
from .providers.filesystem import FileSystemLibraryProvider
from .providers.zookeeper import ZooKeeperLibraryProvider
#

L = logging.getLogger(__name__)

#


class LibraryService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		provider = asab.Config["library"]["path"]

		if provider.startswith("zk://"):
			self.Provider = ZooKeeperLibraryProvider(self.App, provider)
		else:
			self.Provider = FileSystemLibraryProvider(self.App, provider)

	async def read(self, file):
		res = await self.Provider.read(file)
		return res

	async def list(self, file):
		res = await self.Provider.list(file)
		return res

	async def finalize(self, app):
		pass
