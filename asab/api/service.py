import os
import asab
import asab.web
import asab.web.rest
from asab.api.log import WebApiLoggingHandler
import logging

##

L = logging.getLogger(__name__)


##


class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		listen = asab.Config["asab:web"]["listen"]
		self.WebContainer = self._initialize_web(app, listen)

		if asab.Config.has_section("asab:zookeeper"]):
			self.ZkContainer = self._initialize_zookeeper(app)
		else:
			self.ZkContainer = None

		# Backward compatability
		self.Container = self.WebContainer

		app.PubSub.subscribe("WebContainer.started!", self._initialize_after_start)


	async def _initialize_after_start(self, event_name, container):

		if self.WebContainer != container:
			return

		if self.ZkContainer is not None:
			await self.ZkContainer.ZooKeeper.ensure_path(self.ZkContainer.ZooKeeperPath + '/run')
			await self.ZkContainer.advertise(
				data=self._build_zookeeper_adv_data(self.App),
				path="run/a.",
			)


	def _build_zookeeper_adv_data(self, app):
		adv_data = {
			'hostname': app.HostName,
		}
		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data


	def _initialize_web(self, app, listen):
		websvc = app.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(
			websvc, "asab:web",
			config={"listen": listen}
		)
		# TODO: refactor to use custom config section, instead of explicitly passing "listen" param?

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(app, level=logging.NOTSET)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging = logging.getLogger()
		self.Logging.addHandler(self.APILogHandler)

		# Add routes
		container.WebApp.router.add_get('/asab/v1/environ', self.environ)
		container.WebApp.router.add_get('/asab/v1/config', self.config)

		container.WebApp.router.add_get('/asab/v1/logs', self.APILogHandler.get_logs)
		container.WebApp.router.add_get('/asab/v1/logws', self.APILogHandler.ws)

		return container


	async def environ(self, request):
		return asab.web.rest.json_response(request, dict(os.environ))


	async def config(self, request):
		# Copy the config and erase all passwords
		result = {}
		for section in asab.Config.sections():
			result[section] = {}
			# Access items in the raw mode (they are not interpolated)
			for option, value in asab.Config.items(section, raw=True):
				if section == "passwords":
					result[section][option] = "***"
				else:
					result[section][option] = value
		return asab.web.rest.json_response(request, result)


	def _initialize_zookeeper(self, app):
		from ..zookeeper import Module as zkModule, ZooKeeperContainer
		app.add_module(zkModule)

		container = ZooKeeperContainer(app, "asab:zookeeper")

		zksvc = app.get_service("asab.ZooKeeperService")
		zksvc.register_container(container)

		return container
