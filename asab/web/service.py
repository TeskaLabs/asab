import logging

from ..abc.service import Service
from .. import Config
from .. import metrics

from .metrics import WebRequestsMetrics


L = logging.getLogger(__name__)


class WebService(Service):
	"""
	Service for running and easy manipulation of the web server.
	It is used for registering and running the web container as well as initialization of web request metrics.

	It should be used together with `asab.web.WebContainer` object that handles the web configuration.

	Examples:

	```python
	from asab.web import Module
	self.add_module(Module)
	web_service = self.get_service("asab.WebService")
	container = asab.web.WebContainer(
		websvc=web_service,
		config_section_name='my:web',
		config={"listen": "0.0.0.0:8080"}
	)
	```
	"""

	ConfigSectionAliases = ["asab:web"]

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		# Web service is dependent on Metrics service
		if Config.getboolean("asab:metrics", "web_requests_metrics", fallback=False):
			app.add_module(metrics.Module)
			self.MetricsService = app.get_service("asab.MetricsService")
			self.WebRequestsMetrics = WebRequestsMetrics(self.MetricsService)
		self.Containers = {}

	async def finalize(self, app):
		for containers in self.Containers.values():
			await containers._stop(app)

	def _register_container(self, container, config_section_name: str):
		self.Containers[config_section_name] = container
		self.App.TaskService.schedule(container._start(self.App))


	@property
	def WebApp(self):
		"""
		An obsolete property only for maintaining backward compatibility. Please use `asab.web.WebContainer.WebApp` instead.
		"""
		return self.WebContainer.WebApp


	@property
	def WebContainer(self):
		"""
		An obsolete property only for maintaining backward compatibility. Please use `asab.web.WebContainer` instead.
		"""
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
