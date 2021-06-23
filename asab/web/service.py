import asyncio
import asab


class WebService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.Containers = {}
		self.App = app


	async def finalize(self, app):
		for containers in self.Containers.values():
			await containers.finalize(app)


	def _register_container(self, container, config_section_name):
		self.Containers[config_section_name] = container
		asyncio.ensure_future(container.initialize(self.App))


	@property
	def WebApp(self):
		'''
		This is here to maintain backward compatibility.
		'''
		try:
			return self.Containers['asab:web'].WebApp
		except KeyError:
			from .container import WebContainer
			return WebContainer(self, 'asab:web').WebApp
