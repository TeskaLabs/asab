import abc

class Service(abc.ABC):
	"""
	Abstract service class
	"""

	def __init__(self, app, service_name):
		self.Name = service_name
		self.App = app
		app._register_service(self)


	# Lifecycle

	async def initialize(self, app):
		pass

	async def finalize(self, app):
		pass
