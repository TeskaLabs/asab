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
		self.WebContainer = self._initialize_web(listen)

		if len(asab.Config["asab:zookeeper"]["servers"]) > 0:
			self.ZkContainer = self._initialize_zookeeper()
		else:
			self.ZkContainer = None

		# Backward compatability
		self.Container = self.WebContainer

		app.PubSub.subscribe("WebContainer.started!", self._on_webcontainer_started)


	async def _on_webcontainer_started(self, event_name, container):

		if self.WebContainer != container:
			return

		if self.ZkContainer is not None:
			await self.ZkContainer.ZooKeeper.ensure_path(self.ZkContainer.ZooKeeperPath + '/run')
			await self.ZkContainer.advertise(
				data=self._build_zookeeper_adv_data(),
				path="run/{}.".format(self.App.__class__.__name__),
			)


	def _build_zookeeper_adv_data(self):
		adv_data = {
			'appclass': self.App.__class__.__name__,
			'hostname': self.App.HostName,
		}
		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data


	def _initialize_web(self, listen):
		websvc = self.App.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(
			websvc, "asab:web",
			config={"listen": listen}
		)
		# TODO: refactor to use custom config section, instead of explicitly passing "listen" param?

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(self.App, level=logging.NOTSET)
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


	def _initialize_zookeeper(self):
		from ..zookeeper import Module as zkModule, ZooKeeperContainer
		self.App.add_module(zkModule)

		container = ZooKeeperContainer(self.App, "asab:zookeeper")

		zksvc = self.App.get_service("asab.ZooKeeperService")
		zksvc.register_container(container)

		return container
