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
		self.Attention_req = [] # content is JSON/dict


	def attention_required(self ,atten_dict):
		# update the list with attention field
		self.Attention_req.append(atten_dict)

		if self.ZkContainer is not None:
			self.ZkContainer.advertise(
				data=self._build_zookeeper_adv_data(),
				path="/run/{}.".format(self.App.__class__.__name__),
			)

	def remove_attention(self,atten_dict):
		# remove from the list with attention field
		self.Attention_req.remove(atten_dict)

		if self.ZkContainer is not None:
			self.ZkContainer.advertise(
				data=self._build_zookeeper_adv_data(),
				path="/run/{}.".format(self.App.__class__.__name__),
			)


	def initialize_web(self, webcontainer=None):
		'''
		Example:

		websvc = self.App.get_service("asab.WebService")
		webcontainer = asab.web.WebContainer(websvc, 'web')
		ApiService.initialize_web(webcontainer)

		Initialize into a default web container:
		ApiService.initialize_web()
		'''
		assert self.WebContainer is None

		if webcontainer is None:
			websvc = self.App.get_service("asab.WebService")
			webcontainer = websvc.WebContainer

		self.WebContainer = webcontainer

		# TODO: Logging level configurable via config file
		self.APILogHandler = WebApiLoggingHandler(self.App, level=logging.NOTSET)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging = logging.getLogger()
		self.Logging.addHandler(self.APILogHandler)

		self.WebHandler = APIWebHandler(self.App, self.WebContainer.WebApp, self.APILogHandler)


	def initialize_zookeeper(self, zoocontainer=None):
		'''
		Example:

		zksvc = self.App.get_service("asab.ZooKeeperService")
		zoocontainer = zksvc.DefaultContainer
		ApiService.initialize_zookeeper(zksvc)


		Initialize into a default zookeeper container:
		ApiService.initialize_zookeeper()
		'''
		assert self.ZkContainer is None

		if zoocontainer is None:
			zksvc = self.App.get_service("asab.ZooKeeperService")
			zoocontainer = zksvc.DefaultContainer

		# get zookeeper-serivice
		self.ZkContainer = zoocontainer
		self.ZkContainer.advertise(
			data=self._build_zookeeper_adv_data(),
			path="/run/{}.".format(self.App.__class__.__name__),
		)


	def _build_zookeeper_adv_data(self):
		adv_data = {
			'appclass': self.App.__class__.__name__,
			'launchtime': datetime.datetime.utcfromtimestamp(self.App.LaunchTime).isoformat() + 'Z',
			'hostname': self.App.HostName,
		}

		if len(self.Attention_req) > 0:
			adv_data['attention'] = self.Attention_req

		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data
