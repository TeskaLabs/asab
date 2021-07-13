import datetime
import logging

# TODO: This must be a relative import
import asab
import asab.web
import asab.web.rest

from .web_handler import APIWebHandler
from .log import WebApiLoggingHandler

##

L = logging.getLogger(__name__)


##


class ApiService(asab.Service):


	def __init__(self, app, service_name="asab.ApiService"):
		super().__init__(app, service_name)
		self.WebContainer = None
		self.ZkContainer = None


	def initialize_web(self, webcontainer):
		'''
		Example:

		websvc = self.App.get_service("asab.WebService")
		webcontainer = asab.web.WebContainer(websvc, 'web')
		ApiService.initialize_web(webcontainer)
		'''
		assert self.WebContainer is None
		self.WebContainer = webcontainer

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(self.App, level=logging.NOTSET)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging = logging.getLogger()
		self.Logging.addHandler(self.APILogHandler)

		self.WebHandler = APIWebHandler(self.App, self.WebContainer.WebApp, self.APILogHandler)


	def initialize_zookeeper(self, zksvc):
		'''
		Example:

		zksvc = self.App.get_service("asab.ZooKeeperService")
		ApiService.initialize_zookeeper(zksvc)
		'''
		assert self.ZkContainer is None

		# get zookeeper-serivice
		self.ZkContainer = zksvc.build_container()
		# TODO: There is something likely missing


		# await self.ZkContainer.ZooKeeper.ensure_path(self.ZkContainer.ZooKeeperPath + '/run')
		# await self.ZkContainer.advertise(
		# 	data=self._build_zookeeper_adv_data(),
		# 	path="run/{}.".format(self.App.__class__.__name__),
		# )


	def _build_zookeeper_adv_data(self):
		adv_data = {
			'appclass': self.App.__class__.__name__,
			'launchtime': datetime.datetime.utcfromtimestamp(self.App.LaunchTime).isoformat(),
			'hostname': self.App.HostName,
		}
		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data
