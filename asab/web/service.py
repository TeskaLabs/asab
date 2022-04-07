import logging
import asyncio
import asab
import asab.metrics


L = logging.getLogger(__name__)


class WebService(asab.Service):

	ConfigSectionAliases = ["asab:web"]

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		# Web service is dependent on Metrics service
		app.add_module(asab.metrics.Module)
		self.MetricsService = app.get_service("asab.MetricsService")
		self.initialize_metrics()

		self.Containers = {}


	async def finalize(self, app):
		for containers in self.Containers.values():
			await containers.finalize(app)


	def initialize_metrics(self):
		self.MaxDurationCounter = self.MetricsService.create_agg_counter(
			"web_requests_duration_max",
			tags={"help": "Counts maximum request duration to asab endpoints per minute."},
		)
		self.MinDurationCounter = self.MetricsService.create_agg_counter(
			"web_requests_duration_min",
			tags={"help": "Counts minimal request duration to asab endpoints per minute."},
			agg=min
		)
		self.RequestCounter = self.MetricsService.create_counter(
			"web_requests",
			tags={
				"unit": "epm",
				"help": "Counts requests to asab endpoints as events per minute.",
			},
		)
		self.DurationCounter = self.MetricsService.create_counter(
			"web_requests_duration",
			tags={
				"unit": "seconds",
				"help": "Counts total requests duration to asab endpoints per minute.",
			},
		)
		self.DurationHistogram = self.MetricsService.create_histogram(
			"web_requests_duration_hist",
			buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 1, 5, 10, 50],
			tags={
				"unit": "seconds",
				"help": "Categorizes requests based on their duration.",
			},
		)


	def _register_container(self, container, config_section_name):
		self.Containers[config_section_name] = container
		asyncio.ensure_future(container.initialize(self.App))


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
		if config_section not in asab.Config.sections():
			# If there is no [web] section, try other aliases for backwards compatibility
			for alias in self.ConfigSectionAliases:
				if alias in asab.Config.sections():
					config_section = alias
					L.warning("Using obsolete web config alias [{}]. Preferred section name is [web]. ".format(alias))
					break
			else:
				raise RuntimeError("No [web] section configured.")

		try:
			return self.Containers[config_section]
		except KeyError:
			from .container import WebContainer
			return WebContainer(self, config_section)
