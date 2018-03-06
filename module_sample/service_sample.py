import asab


class ServiceSample(asab.Service):


	def __init__(self, app):
		super().__init__(app)
		app.PubSub.subscribe_all(self)

		self.value = asab.Config["module_sample"]["example"]


	def hello(self):
		print(self.value, "<<<<")


	@asab.subscribe("Application.tick!")
	def on_tick(self, event_name):
		print("Service tick!")
