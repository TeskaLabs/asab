import logging
import asab

from .service import LibraryService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:library': {
			'provider': 'zk://zookeeper-1:2181/library'
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		L.info("Sample module loaded.")

		self.service = LibraryService(app, "asab.LibraryService")


	async def initialize(self, app):
		L.info("Sample module initialized.")
		app.PubSub.subscribe_all(self)


	async def finalize(self, app):
		L.info("Sample module finalized.")