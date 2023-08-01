import abc
from ..application import Application


class Service(abc.ABC):
	"""
	Abstract class for ASAB services.

	Service objects are registered at the service registry `asab.Application.Services`, managed by an application object.

	Examples:

	This is how Service is created and registered:
	```python
	my_service = MyService(app, "my_service")
	```

	This is how Service is located and used:

	```python
	my_service = app.get_service("my_service")
	my_service.service_method()
	```

	Example of a typical Service class skeleton:

	```python
	class MyService(asab.Service):
		def __init__(self, app, service_name):
			super().__init__(app, service_name)
			...

		async def initialize(self, app):
			...

		async def finalize(self, app):
			...

		def service_method(self):
			...
	```
	"""

	def __init__(self, app: Application, service_name: str):
		"""
		Register the service to `asab.Application.Services` dictionary with the provided `service_name`.

		Args:
			app: Reference to ASAB application.
			service_name: Reference name of the Service.
		"""
		self.Name = service_name
		self.App = app
		app._register_service(self)

	# Lifecycle

	async def initialize(self, app: Application):
		"""
		This method is called when the Service is initialized.
		It can be overridden by an user.

		Args:
			app: Reference to ASAB application.
		"""
		pass

	async def finalize(self, app: Application):
		"""
		This method is called when the Service is finalized, e.g., during application `exit-time`.
		It can be overridden by an user.

		Args:
			app: Reference to ASAB application.
		"""
		pass
