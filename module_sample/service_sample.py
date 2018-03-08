import logging
import asab

#

L = logging.getLogger(__name__)

#


class ServiceSample(asab.Service):


	def __init__(self, app):
		super().__init__(app)
		app.PubSub.subscribe_all(self)

		self.value = asab.Config["module_sample"]["example"]
		self.counter = 0


	async def initialize(self, app):
		L.info("Sample service initialized.")


	async def finalize(self, app):
		L.info("Sample service finalized.")


	def hello(self):
		L.info(self.value)


	@asab.subscribe("Application.tick!")
	async def on_tick(self, event_name):
		self.counter=self.counter+1
		L.info("Service tick!", struct_data={"counter":self.counter})
