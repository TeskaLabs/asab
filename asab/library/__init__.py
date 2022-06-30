import logging
import asab

from .service import LibraryService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'library': {
			'providers': 'zk://zookeeper-1:2181/library'
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.App = app
		self.service = LibraryService(self.App, "asab.LibraryService")


	async def initialize(self, app):
		pass


	async def finalize(self, app):
		pass
