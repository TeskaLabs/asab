import os
import json
import asyncio
import logging
import urllib.parse
import configparser

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
		# A server is defined as `address:port` format.
		# Example:
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181"
		# If servers are empty, default from [zookeeper]/servers will be taken
		# If [zookeeper]/servers value is not provided, ZOOKEEPER_SERVERS environment variable is used
		"servers": "",

		# If not provided, "/asab" path will be used
		"path": "",
	}


	def __init__(self, zksvc, config_section_name, config=None, z_path=None):
		"""
		Zookeeper cofiguration:

		* Source 1: Obtain Zookeeper configuration from the configuration section specified by `config_section_name` argument

		* Source 2: Obtain Zookeeper configuration from `z_path` argument, which is Zookeeper URL (see below)

		* Source 3: `ZOOKEEPER_SERVERS` environment variable


		The `z_path` argument has precedence over config but the implementation will look
		at configuration if `z_path` URL is missing completely or partially.

		Supported types of z_path` URLs:

		1. Absolute URL
			Example: zookeeper://zookeeper:12181/etc/configs/file1

			There is no fallback to the configuration.



		2. Relative URL with full path
			Example: zookeeper:///etc/configs/file1

			In this case the relative url is expanded as follows:
			zookeeper://{zookeeper_server}/etc/configs/file1

			Where {zookeeper_server} is substituted with the server entry of the [zookeeper] configuration file section.



		3. Relative URL with relative path

			Example: zookeeper:./etc/configs/file1
				In this case, the relative URL is expanded as follows:

				zookeper://{zookeeper_server}/{zookeeper_path}/etc/configs/file1
				Where {zookeeper_server} is substituted with the "server" entry of the [zookeeper] configuration file section and
				{zookeeper_path} is substituted with the "path" entry of the [zookeeper] configuration file section.

		Sample config file:
		[zookeeper]
		server=server1:port1,server2:port2,server3:port3
		path=myfolder

		"""
		super().__init__(config_section_name=config_section_name, config=config)
		self.App = zksvc.App

		# Parse URL from z_path
		if z_path is not None:
			url_pieces = urllib.parse.urlparse(z_path)
			url_netloc = url_pieces.netloc
			url_path = url_pieces.path
		else:
			url_netloc = ""
			url_path = ""

		# If there is no location, use the value of 'servers' from the configuration
		if url_netloc == "":
			url_netloc = self.Config.get("servers", "")

		if url_netloc == "":
			from ..config import Config
			try:
				url_netloc = Config.get("zookeeper", "servers")
			except (configparser.NoOptionError, configparser.NoSectionError):
				pass

		if url_netloc == "":
			url_netloc = os.environ.get("ZOOKEEPER_SERVERS", "")

		if url_netloc == "":
			# if server entry is missing exit
			L.critical("Cannot connect to Zookeeper, the configuration of the server address is not available.")
			raise SystemExit("Exit due to a critical configuration error.")

		assert url_netloc is not None

		# If path has not been provided, use the value of 'path' from the configuration
		if url_path == "":
			url_path = self.Config.get("path", "")

		if url_path == "":
			from ..config import Config
			try:
				url_path = Config.get("zookeeper", "path")
			except (configparser.NoOptionError, configparser.NoSectionError):
				pass

		if url_path == "":
			url_path = 'asab'

		# Remove all heading '/' from path
		while url_path.startswith('/'):
			url_path = url_path[1:]

		self.ZooKeeper = KazooWrapper(zksvc, url_netloc)
		self.Path = url_path

		self.Advertisments = dict()
		self.DataWatchers = set()
		self.App.PubSub.subscribe("Application.tick/300!", self._readvertise)

		zksvc.Containers.append(self)
		zksvc.ProactorService.schedule(self._start, self.App)


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

		self.ZooKeeper.Client.ensure_path(self.Path)

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


	# Advertisement into Zookeeper

	def advertise(self, data, path):
		adv = self.Advertisments.get(self.Path + path)
		if adv is None:
			adv = ZooKeeperAdvertisement(self.Path + path)
			self.Advertisments[self.Path + path] = adv
		self.App.TaskService.schedule(adv._set_data(self, data))


	async def _readvertise(self, *args):
		for adv in self.Advertisments.values():
			await adv._readvertise(self)


	# Reading

	async def get_children(self):
		return await self.ZooKeeper.get_children(self.Path)

	async def get_data(self, child, encoding="utf-8"):
		raw_data = await self.get_raw_data(child)
		if raw_data is None:
			return {}
		return json.loads(raw_data.decode(encoding))

	async def get_raw_data(self, child):
		return await self.ZooKeeper.get_data("{}/{}".format(self.Path, child))


	# Watcher

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
		self.Data = None

		self.Path = path
		self.RealPath = None

		self.Lock = asyncio.Lock()


	async def _set_data(self, zoocontainer, data):
		async with self.Lock:
			if isinstance(data, dict):
				self.Data = json.dumps(data).encode("utf-8")
			elif isinstance(data, str):
				self.Data = data.encode("utf-8")
			else:
				self.Data = data

			def write_to_zk():
				if self.RealPath is None:
					self.RealPath = zoocontainer.ZooKeeper.Client.create(self.Path, self.Data, sequence=True, ephemeral=True, makepath=True)
				else:
					try:
						zoocontainer.ZooKeeper.Client.set(self.RealPath, self.Data)
					except kazoo.exceptions.NoNodeError:
						self.RealPath = zoocontainer.ZooKeeper.Client.create(self.Path, self.Data, sequence=True, ephemeral=True, makepath=True)

			await zoocontainer.ZooKeeper.ProactorService.execute(write_to_zk)


	async def _readvertise(self, zoocontainer):
		if self.Data is None:
			return

		if self.RealPath is None:
			return

		async with self.Lock:

			def check_at_zk():
				if zoocontainer.ZooKeeper.Client.exists(self.RealPath):
					return

				# If the advertisement node is not present in the Zookeeper, force the recreation
				self.RealPath = zoocontainer.ZooKeeper.Client.create(self.Path, self.Data, sequence=True, ephemeral=True)

			await zoocontainer.ZooKeeper.ProactorService.execute(check_at_zk)
