import os
import datetime
import logging

# TODO: This must be a relative import
import asab
import asab.web
import asab.web.rest
import aiohttp
from asab.api.log import WebApiLoggingHandler

##

L = logging.getLogger(__name__)


##


class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.WebApp = self._initialize_web()

		if len(asab.Config["asab:zookeeper"]["servers"]) > 0:
			self.ZkContainer = self._initialize_zookeeper()
		else:
			self.ZkContainer = None


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
			'launchtime': datetime.datetime.utcfromtimestamp(self.App.LaunchTime).isoformat(),
			'hostname': self.App.HostName,
		}
		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data


	def _initialize_web(self):
		websvc = self.App.get_service("asab.WebService")

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(self.App, level=logging.NOTSET)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging = logging.getLogger()
		self.Logging.addHandler(self.APILogHandler)

		# Add routes
		websvc.WebApp.router.add_get('/asab/v1/environ', self.environ)
		websvc.WebApp.router.add_get('/asab/v1/config', self.config)

		websvc.WebApp.router.add_get('/asab/v1/logs', self.APILogHandler.get_logs)
		websvc.WebApp.router.add_get('/asab/v1/logws', self.APILogHandler.ws)

		websvc.WebApp.router.add_get('/asab/v1/changelog', self.changelog)

		return websvc.WebApp


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

		from ..zookeeper import Module as zkModule
		self.App.add_module(zkModule)

		# get zookeeper-serivice
		zksvc = self.App.get_service("asab.ZooKeeperService")
		return zksvc.build_container()


	def changelog_path(self):
		path = asab.Config.get('general', 'changelog_path')
		if os.path.isfile(path):
			return path
		if os.path.isfile('/CHANGELOG.md'):
			return '/CHANGELOG.md'
		if os.path.isfile('CHANGELOG.md'):
			return 'CHANGELOG.md'
		return None


	def changelog(self, request):
		path = self.changelog_path()

		if path is None:
			return aiohttp.web.HTTPNotFound()

		with open(path) as f:
			result = f.read()
		return aiohttp.web.Response(text=result, content_type='text/markdown')
