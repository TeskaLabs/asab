import logging

from ..abc.service import Service
from .. import Config
from .. import metrics

from .metrics import WebRequestsMetrics


L = logging.getLogger(__name__)


class WebService(Service):

	ConfigSectionAliases = ["asab:web"]

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		# Web service is dependent on Metrics service
		app.add_module(metrics.Module)
		self.MetricsService = app.get_service("asab.MetricsService")
		self.WebRequestsMetrics = WebRequestsMetrics(self.MetricsService)
		self.Containers = {}


	async def finalize(self, app):
		for containers in self.Containers.values():
			await containers._stop(app)

	def _register_container(self, container, config_section_name):
		self.Containers[config_section_name] = container
		self.App.TaskService.schedule(container._start(self.App))


	@property
	def WebApp(self):
		'''
		This is here to maintain backward compatibility.
		'''
		return self.WebContainer.WebApp


	@property
	def WebContainer(self):
		'''
		This is here to maintain backward compatibility.
		'''
		config_section = "web"

		# The WebContainer should be configured in the config section [web]
		if config_section not in Config.sections():
			# If there is no [web] section, try other aliases for backwards compatibility
			for alias in self.ConfigSectionAliases:
				if alias in Config.sections():
					config_section = alias
					L.warning("Using obsolete config section [{}]. Preferred section name is [web]. ".format(alias))
					break
			else:
				raise RuntimeError("No [web] section configured.")

		try:
			return self.Containers[config_section]
		except KeyError:
			from .container import WebContainer
			return WebContainer(self, config_section)
