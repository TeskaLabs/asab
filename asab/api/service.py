import os
import uuid
import json
import datetime
import logging
import typing

from .. import Service, Config
from ..utils import running_in_container
from .web_handler import APIWebHandler
from .log import WebApiLoggingHandler
from .doc import DocWebHandler
from .discovery import DiscoveryService

##

L = logging.getLogger(__name__)


##


class ApiService(Service):

	def __init__(self, app, service_name="asab.ApiService"):
		super().__init__(app, service_name)

		self.WebContainer = None
		self.ZkContainer = None
		self.MetricWebHandler = None

		self.AttentionRequired = {}  # dict of errors found.
		self.Discovery = {}

		# Manifest
		path = Config.get("general", "manifest")
		if path == "":

			if os.path.isfile("/app/MANIFEST.json"):
				path = "/app/MANIFEST.json"
			elif os.path.isfile("/MANIFEST.json"):
				path = "/MANIFEST.json"
			elif os.path.isfile("MANIFEST.json"):
				path = "MANIFEST.json"

		if len(path) != 0:
			try:
				with open(path) as f:
					self.Manifest = json.load(f)
			except Exception as e:
				L.exception("Error when reading manifest for reason {}".format(e))

		else:
			self.Manifest = None

		# Change log
		path = Config.get("general", "changelog")
		if path == "":
			if os.path.isfile("/app/CHANGELOG.md"):
				path = "/app/CHANGELOG.md"
			elif os.path.isfile("/CHANGELOG.md"):
				path = "/CHANGELOG.md"
			elif os.path.isfile("CHANGELOG.md"):
				path = "CHANGELOG.md"

		if os.path.isfile(path):
			self.ChangeLog = path
		else:
			self.ChangeLog = None

		# Service Discovery
		self.DiscoveryService = None


	def attention_required(self, att: dict, att_id=None):

		if att_id is None:
			# add new attention id to list
			att_id = uuid.uuid4().hex
		self.AttentionRequired[att_id] = att

		# if creation time for att_id is not present then add
		if "_c" not in att:
			att["_c"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

		# add to microservice json/dict section attention_required
		self._do_zookeeper_adv_data()
		return att_id


	def remove_attention(self, att_id):
		try:
			# find the attention id value and remove it.
			for error_key, error_value in self.AttentionRequired.items():
				if error_key == att_id:
					del self.AttentionRequired[att_id]
					break
		except KeyError:
			L.warning("Key None does not exist.")
			raise Exception("Key None does not exist.")

		self._do_zookeeper_adv_data()


	def update_discovery(self, discovery_dict: typing.Dict[str, list]):
		"""
		Updates the `discovery` attribute of the data advertised to ZooKeeper.
		When updating already existing record, list all identifiers of each type. Previous list of identifiers is overwritten by the new one.

		Args:
			discovery_dict (typing.Dict[str, list]): The `discovery_dict` parameter is a dictionary where the
		keys are strings specifying type of an identifier (e.g. baseline_id) and the values are sets of the identifiers.
		"""

		for k, v in discovery_dict.items():
			assert isinstance(k, str)
			assert isinstance(v, list)  # set is not JSON serializable

		self.Discovery.update(discovery_dict)

		self._do_zookeeper_adv_data()


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

		self.WebHandler = APIWebHandler(self, self.WebContainer.WebApp, self.APILogHandler)

		self.DocWebHandler = DocWebHandler(self, self.App, self.WebContainer)

		# If asab.MetricsService is available, initialize its web handler
		metrics_svc = self.App.get_service("asab.MetricsService")
		if metrics_svc is not None:
			from ..metrics.web_handler import MetricWebHandler
			self.MetricWebHandler = MetricWebHandler(metrics_svc, self.WebContainer.WebApp)

		self.App.PubSub.subscribe("WebContainer.started!", self._on_webcontainer_start)


	def initialize_zookeeper(self, zoocontainer=None):
		'''
		Example:

		Initialize into a default zookeeper container:

		```
		ApiService.initialize_zookeeper()
		```


		Intialize with a custom Zookeeper container:

		```
		zksvc = self.App.get_service("asab.ZooKeeperService")
		zoocontainer = ZooKeeperContainer(zksvc, "mycontainer")
		ApiService.initialize_zookeeper(zoocontainer)
		```

		'''
		assert self.ZkContainer is None

		if zoocontainer is None:
			zksvc = self.App.get_service("asab.ZooKeeperService")
			from ..zookeeper import ZooKeeperContainer
			zoocontainer = ZooKeeperContainer(zksvc)

		# get zookeeper-service
		self.ZkContainer = zoocontainer

		# initialize service discovery
		self.DiscoveryService = DiscoveryService(self.App, self.ZkContainer)

		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zkcontainer_start)
		self._do_zookeeper_adv_data()


	def _do_zookeeper_adv_data(self):
		if self.ZkContainer is None:
			return

		if not self.ZkContainer.is_connected():
			return

		adv_data = {
			'host': self.App.HostName,
			'appclass': self.App.__class__.__name__,
			'launch_time': datetime.datetime.fromtimestamp(self.App.LaunchTime, datetime.timezone.utc).isoformat(),
			'process_id': os.getpid(),
		}

		# A unique identifier of a microservice; added as an environment variable
		instance_id = os.getenv('INSTANCE_ID', None)
		if instance_id is not None:
			adv_data["instance_id"] = instance_id

		# An identifier of the host machine (node); added if available at environment variables
		node_id = os.getenv('NODE_ID', None)
		if node_id is not None:
			adv_data["node_id"] = node_id

		service_id = os.getenv('SERVICE_ID', None)
		if service_id is not None:
			if service_id != service_id.lower():
				L.warning("Service ID should be lowercase.")
			adv_data["service_id"] = service_id

		# An identifier of a site, of a specific deployment
		site_id = os.getenv('SITE_ID', None)
		if site_id is not None:
			adv_data["site_id"] = site_id

		if running_in_container():
			adv_data["containerized"] = True

		if self.Manifest is not None:
			adv_data.update(self.Manifest)

		if len(self.AttentionRequired) > 0:
			# add attention required status
			adv_data.update({"attention_required": self.AttentionRequired})

		if len(self.Discovery) > 0:
			adv_data.update({"discovery": self.Discovery})

		if self.WebContainer is not None:
			adv_data['web'] = self.WebContainer.Addresses

		self.ZkContainer.advertise(
			data=adv_data,
			path="/run/{}.".format(self.App.__class__.__name__),
		)


	def _on_zkcontainer_start(self, message_type, container):
		if container == self.ZkContainer:
			self._do_zookeeper_adv_data()

	def _on_webcontainer_start(self, message_type, container):
		if container == self.WebContainer:
			self._do_zookeeper_adv_data()
