from asab.abc.service import Service


class ServiceSample(Service):

	def __init__(self, app):
		super().__init__(app)

	def hello(self):
		print("Hello world.")
