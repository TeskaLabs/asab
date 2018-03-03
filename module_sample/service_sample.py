import asab


class ServiceSample(asab.Service, asab.Subscriber):


	def __init__(self, app):
		super().__init__(app)
		self.subscribe(app)

		self.value = asab.Config["module_sample"]["example"]


	def hello(self):
		print(self.value, "<<<<")


	@asab.subscribe("tick")
	def on_tick(self, event_name):
		print("Service tick")
