import json
import asyncio
import logging

import kazoo.exceptions
import kazoo.recipe.watchers

from .wrapper import KazooWrapper
from ..config import ConfigObject

#

L = logging.getLogger(__name__)

#


class ZooKeeperContainer(ConfigObject):


	ConfigDefaults = {
		# Server list to which ZooKeeper Client tries connecting.
		# Specify a comma (,) separated server list.
		# A server is defined as address:port format.
		# Example:
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181"
		#
		# WARNING: If the value is not provided (empty string), Zookeeper container refuses to start
		"servers": "",

		# The default is an application class name
		"path": "",
	}


	def __init__(self, zksvc, config_section_name, config=None, z_path=None):
		"""
		Alternative 1: Obtain Zookeeper container with `config_section_name` configuration section
		Alternative 2: Obtain Zookeeper container with call z_path (URL)
		Example:
		zk_cnt = ZooKeeperContainer(app, config_section_name='', z_path=z_path)
		"""
		super().__init__(config_section_name=config_section_name, config=config)

		self.App = zksvc.App
		self.ConfigSectionName = config_section_name
		self.ZooKeeper = KazooWrapper(zksvc.App, self.Config, z_path)
		self.ZooKeeperPath = self.ZooKeeper.Path
		self.Advertisments = dict()
		self.DataWatchers = set()
		self.App.PubSub.subscribe("Application.tick/300!", self._do_advertise)

		zksvc._register_container(self)


	def _start(self, app):
		# This method is called on proactor thread
		try:
			self.ZooKeeper._start()
		except Exception as e:
			L.error(
				"Failed to connect to ZooKeeper: {}".format(e),
				struct_data={
					'hosts': str(self.ZooKeeper.Hosts)
				}
			)
			return

		self.ZooKeeper.Client.ensure_path(self.ZooKeeper.Path)

		def in_main_thread():
			self.App.PubSub.publish("ZooKeeperContainer.started!", self)

		self.App.Loop.call_soon_threadsafe(in_main_thread)


	async def _stop(self, app):
		await self.ZooKeeper._stop()


	def is_connected(self):
		"""
		Check, if the Zookeeper is connected
		"""
		return self.ZooKeeper.Client.connected


	def advertise(self, data, path):
		adv = self.Advertisments.get(self.ZooKeeper.Path + path)
		if adv is None:
			adv = ZooKeeperAdvertisement(self.ZooKeeper.Path + path)
			self.Advertisments[self.ZooKeeper.Path + path] = adv
		adv.set_data(data)
		self.App.TaskService.schedule(adv._do_advertise(self))


	async def _do_advertise(self, *args):
		for adv in self.Advertisments.values():
			await adv._do_advertise(self)

	async def get_children(self):
		return await self.ZooKeeper.get_children(self.ZooKeeper.Path)

	async def get_data(self, child, encoding="utf-8"):
		raw_data = await self.get_raw_data(child)
		if raw_data is None:
			return {}
		return json.loads(raw_data.decode(encoding))

	async def get_raw_data(self, child):
		return await self.ZooKeeper.get_data("{}/{}".format(self.ZooKeeper.Path, child))

	def _on_watcher_trigger(self, data, stat):
		def on_watcher_trigger():
			self.App.PubSub.publish(self.App.PubSub.publish("ZooKeeper.watcher!", data, stat))
		self.App.Loop.call_soon_threadsafe(on_watcher_trigger)


	async def create_watcher(self, client, path):
		# Do this in executor
		watcher = kazoo.recipe.watchers.DataWatch(client, path, func=self._on_watcher_trigger)
		self.DataWatchers.add(watcher)


class ZooKeeperAdvertisement(object):

	def __init__(self, path):
		self.Path = path
		self.Data = None
		self.Node = None
		self.Lock = asyncio.Lock()


	def set_data(self, data):
		if isinstance(data, dict):
			self.Data = json.dumps(data).encode("utf-8")
		elif isinstance(data, str):
			self.Data = data.encode("utf-8")
		else:
			self.Data = data


	async def _do_advertise(self, zoocontainer):
		if self.Data is None:
			return

		async with self.Lock:
			if self.Node is not None and await zoocontainer.ZooKeeper.exists(self.Node):
				await zoocontainer.ZooKeeper.set_data(self.Node, self.Data)
				return

			# Parms description
			# self.Path. Path to be created
			# self.Data. Data in the path
			# sequential=True. Path is suffixed with a unique index.
			# ephemeral=True. Node created is ephemeral

			async def create():
				self.Node = await zoocontainer.ZooKeeper.create(self.Path, self.Data, True, True)

			try:
				await create()
			except kazoo.exceptions.NoNodeError:
				await zoocontainer.ZooKeeper.ensure_path(self.Path.rstrip(self.Path.split("/")[-1]))
				await create()
