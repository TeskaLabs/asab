import asab


class ServiceSample(asab.Service):

	def __init__(self, app):
		super().__init__(app)

	def hello(self):
		print("Hello world.")
