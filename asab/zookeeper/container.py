import os
import json
import asyncio
import logging
import urllib.parse
import configparser

import kazoo.exceptions
import kazoo.recipe.watchers
import kazoo.protocol.states

from .wrapper import KazooWrapper
from ..config import ConfigObject

#

L = logging.getLogger(__name__)

#


class ZooKeeperContainer(ConfigObject):
	"""
	Create a Zookeeper container with a specifications of the connectivity.
	"""

	ConfigDefaults = {
		# Server list to which ZooKeeper Client tries connecting.
		# Specify a comma (,) separated server list.
		# A server is defined as `address:port` format.
		# Example:
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181"
		# If servers are empty, default from [zookeeper]/servers will be taken
		# If [zookeeper]/servers value is not provided, ASAB_ZOOKEEPER_SERVERS environment variable is used
		"servers": "",

		# If not provided, "/asab" path will be used
		"path": "",
	}


	def __init__(self, zookeeper_service, config_section_name="zookeeper", config=None, z_path=None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.App = zookeeper_service.App
		self.ConfigSectionName = config_section_name
		self.ProactorService = zookeeper_service.ProactorService

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
			url_netloc = os.environ.get("ASAB_ZOOKEEPER_SERVERS", "")

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

		self.Path = url_path

		self.Advertisments = dict()
		self.DataWatchers = set()
		self.App.PubSub.subscribe("Application.tick/300!", self._readvertise)

		self.ZooKeeper = KazooWrapper(self, url_netloc)

		zookeeper_service.Containers.append(self)
		self.ProactorService.schedule(self._start)


	def _start(self):
		# This method is called on proactor thread
		try:
			self.ZooKeeper.Client.start()
		except Exception as e:
			L.error(
				"Failed to connect to ZooKeeper: {}".format(e),
				struct_data={
					'hosts': str(self.ZooKeeper.Client.hosts),
				}
			)


	async def _stop(self):
		await self.ZooKeeper._stop()


	def _listener(self, state):
		'''
		Generate PubSub events:

		* ZooKeeperContainer.state/CONNECTED!
		* ZooKeeperContainer.state/LOST!
		* ZooKeeperContainer.state/SUSPENDED!
		'''
		if state == kazoo.protocol.states.KazooState.CONNECTED:
			self.App.Loop.call_soon_threadsafe(self.ZooKeeper.Client.ensure_path, self.Path)

		self.App.PubSub.publish_threadsafe("ZooKeeperContainer.state/{}!".format(state), self)



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

	async def get_children(self, path=""):
		return await self.ZooKeeper.get_children("{}/{}".format(self.Path, path))

	async def get_data(self, path, encoding="utf-8"):
		raw_data = await self.get_raw_data(path)
		if raw_data is None:
			return {}
		return json.loads(raw_data.decode(encoding))

	async def get_raw_data(self, path):
		return await self.ZooKeeper.get_data("{}/{}".format(self.Path, path))


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
