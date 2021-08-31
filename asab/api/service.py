import datetime
import logging
import asab.web.rest
import uuid

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
		self.AttentionRequired = []  # dictionary of keys

	def attention_required(self, attention_key_value=None):

		if attention_key_value is None:
			# add new error id to list
			attention_key_value = str(uuid.uuid4())
			new_key = {'id': attention_key_value}
			self.AttentionRequired.append(new_key)

		# update the microservice json/dict section attention_required
		if self.ZkContainer is not None:
			self.ZkContainer.advertise(
				data=self._build_zookeeper_adv_data(),
				path="/run/{}.".format(self.App.__class__.__name__),
			)
		return attention_key_value

	def remove_attention(self, attention_key):
		try:
			# find the error value that is resolved and remove it.
			for error_key_dict in self.AttentionRequired:
				for err_key, err_value in error_key_dict.items():
					if err_value == attention_key:
						del error_key_dict[err_key]
						break
		except KeyError:
			L.warning("Key None does not exist.")
			raise Exception("Key None does not exist.")

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

		if len(self.AttentionRequired) > 0:
			adv_data.update({"attention_required": self.AttentionRequired})

		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses
		return adv_data
