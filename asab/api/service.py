import datetime
import logging

# TODO: This must be a relative import
import asab
import asab.web
import asab.web.rest

from web_handler import APIWebHandler
from .log import WebApiLoggingHandler

##

L = logging.getLogger(__name__)


##


class ApiService(asab.Service):


	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.WebHandler = None
		self.ZkContainer = None


	def initialize_web(self, webapp):
		'''
		Example:

		websvc = self.App.get_service("asab.WebService")
		ApiService.initialize_web(websvc.WebApp)
		'''
		assert self.WebHandler is None

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(self.App, level=logging.NOTSET)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging = logging.getLogger()
		self.Logging.addHandler(self.APILogHandler)

		self.WebHandler = APIWebHandler(self.App, webapp)


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


	def _build_zookeeper_adv_data(self):
		adv_data = {
			'appclass': self.App.__class__.__name__,
			'launchtime': datetime.datetime.utcfromtimestamp(self.App.LaunchTime).isoformat(),
			'hostname': self.App.HostName,
		}
		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data
