import logging
import asyncio
import asab


L = logging.getLogger(__name__)


class WebService(asab.Service):
	ObsoleteConfigAliases = ["asab:web"]

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
		if "web" in asab.Config.sections():
			# The WebContainer should be configured in the config section [web]
			config_section_name = "web"
		else:
			# Supporting other section names for backwards compatibility
			for alias in self.ObsoleteConfigAliases:
				if alias in asab.Config.sections():
					config_section_name = alias
					L.warning("Using obsolete web config alias [{}]. Preferred section name is [web]. ".format(alias))
					break
			else:
				raise RuntimeError("No [web] section configured.")

		try:
			return self.Containers[config_section_name].WebApp
		except KeyError:
			from .container import WebContainer
			return WebContainer(self, config_section_name).WebApp
