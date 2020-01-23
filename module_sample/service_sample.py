import logging
import asab

#

L = logging.getLogger(__name__)

#


class ServiceSample(asab.Service):


	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		app.PubSub.subscribe_all(self)

		self.value = asab.Config["module_sample"]["example"]
		self.counter = 0


	async def initialize(self, app):
		L.info("Sample service initialized.")


	async def finalize(self, app):
		L.info("Sample service finalized.")


	def hello(self):
		L.debug(self.value)
		L.info(self.value)
		L.warning(self.value)
		L.error(self.value)
		L.fatal(self.value)


	@asab.subscribe("Application.tick!")
	async def on_tick(self, message_type):
		self.counter = self.counter + 1
		L.info(message_type, struct_data={"counter": self.counter})
