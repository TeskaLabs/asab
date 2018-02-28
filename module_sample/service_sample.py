import asab


class ServiceSample(asab.Service):

	def __init__(self, app):
		super().__init__(app)
		self.value = asab.Config["module_sample"]["example"]

	def hello(self):
		print(self.value)
