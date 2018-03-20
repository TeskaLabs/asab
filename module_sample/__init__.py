import logging
import asab

from .service_sample import ServiceSample

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'module_sample': {
			'example': 'Hello world.'
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		L.info("Sample module loaded.")

		self.service = ServiceSample(app, "service_sample")


	async def initialize(self, app):
		L.info("Sample module initialized.")
		app.PubSub.subscribe_all(self)


	async def finalize(self, app):
		L.info("Sample module finalized.")
