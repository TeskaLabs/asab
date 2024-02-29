import os
import json
import logging

from .exception import ASABConfigException, ErrorCode

###

L = logging.getLogger(__name__)


###

class ZooKeeperProvider():

	def __init__(self, app, zk_container):
		self.ZooKeeperContainer = zk_container
		self.ZK = self.ZooKeeperContainer.ZooKeeper
		self.ConfigPath = self.ZooKeeperContainer.Path + "/config"
		self.App = app

		self.IsReady = False
		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_connected)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/SUSPENDED!", self._on_zk_lost)

	# Lifecycle

	async def _on_zk_connected(self, event_name, zookeeper):
		if zookeeper != self.ZooKeeperContainer:
			return
		
		await self.ZooKeeperContainer.ZooKeeper.ensure_path(self.ConfigPath)
		self._set_ready(ready=True)
		self.App.PubSub.publish("ASABConfig.ready!")

	async def _on_zk_lost(self, event_name, zkcontainer):
		if zkcontainer != self.ZooKeeperContainer:
			return
		self._set_ready(ready=False)

	def _set_ready(self, ready=True):
		self.IsReady = ready

	async def finalize(self, app):
		await self.ZK._stop()

	# Config

	async def list_configs(self, config_type) -> list:
		"""
		List configs for the given config type.self.App.PubSub.publish("ASABConfig.ready!")
		"""
		if not self.IsReady:
			raise ASABConfigException(ErrorCode.ZOOKEEPER_LOST, {"config_type": config_type}, tech_message="Connection to ZooKeeper lost. Action could not be proceeed.")
		res = await self.ZK.get_children(os.path.join(self.ConfigPath, config_type))
		if res is None:
			raise ASABConfigException(ErrorCode.CONFIGS_MISSING, {"path": os.path.join(self.ConfigPath, config_type), "config_type": config_type}, tech_message="Configs of config type '{}' were not found.".format(config_type))
		return res

	async def get_config(self, config_type, config_name):
		"""
		Get a configuration file from a specified path, check if it
		exists, and parse it as JSON.
		"""
		if not self.IsReady:
			raise ASABConfigException(ErrorCode.ZOOKEEPER_LOST, {"config_type": config_type, "config_name": config_name}, tech_message="Connection to ZooKeeper lost. Action could not be proceeed.")
		path = os.path.join(self.ConfigPath, config_type, config_name)

		data = await self.ZK.get_data(path)
		if data is None:
			raise ASABConfigException(ErrorCode.CONFIG_MISSING, {"path": path, "config_type": config_type, "config_name": config_name}, tech_message="Config '{}' of config type '{}' was not found.".format(config_name, config_type))
		try:
			return json.loads(data)
		except json.decoder.JSONDecodeError as e:
			raise ASABConfigException(ErrorCode.INVALID_JSON, {"path": path, "config_type": config_type, "config_name": config_name, "reason": str(e)}, tech_message="Config '{}' of config type '{}' doesn't have a valid JSON format.".format(config_name, config_type))

	# Config type

	async def list_config_types(self):
		if not self.IsReady:
			raise ASABConfigException(ErrorCode.ZOOKEEPER_LOST, tech_message="Connection to ZooKeeper lost. Action could not be proceeed.")
		res = await self.ZK.get_children(self.ConfigPath)
		if res is None:
			raise ASABConfigException(ErrorCode.CONFIGS_MISSING, {"path": os.path.join(self.ConfigPath)}, tech_message="No config types available.")
		return res

	async def get_config_type(self, config_type):
		if not self.IsReady:
			raise ASABConfigException(ErrorCode.ZOOKEEPER_LOST, tech_message="Connection to ZooKeeper lost. Action could not be proceeed.")
		path = os.path.join(self.ConfigPath, config_type)
		data = await self.ZK.get_data(path)
		if data is None:
			raise ASABConfigException(ErrorCode.CONFIG_TYPE_MISSING, {"path": path, "config_type": config_type}, tech_message="Config type '{}' was not found.".format(config_type))
		try:
			return json.loads(data)
		except json.decoder.JSONDecodeError as e:
			raise ASABConfigException(ErrorCode.INVALID_JSON, {"path": path, "config_type": config_type, "reason": str(e)}, tech_message="Config type '{}' doesn't have a valid JSON format.".format(config_type))
