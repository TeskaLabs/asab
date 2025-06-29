import os
import json
import logging
import threading
import dataclasses
import urllib.parse
import configparser

import kazoo.exceptions
import kazoo.recipe.watchers
import kazoo.protocol.states

from .wrapper import KazooWrapper
from ..config import Configurable
from ..log import LOG_NOTICE

#

L = logging.getLogger(__name__)

#


class ZooKeeperContainer(Configurable):
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
		self.AdvertismentsLock = threading.Lock()

		self.App.PubSub.subscribe("Application.tick/300!", self._on_tick300)
		self.App.PubSub.subscribe("Application.tick/60!", self._on_tick60)

		self.ZooKeeper = KazooWrapper(self, url_netloc)

		zookeeper_service.Containers.append(self)
		self.ZooKeeper.Client.start_async()


	def _on_tick60(self, *args):
		# Reconnect if the connection is lost
		if self.ZooKeeper.Client.state == kazoo.protocol.states.KazooState.LOST and self.ZooKeeper.Client.client_state == kazoo.protocol.states.KeeperState.CLOSED and not self.ZooKeeper.Stopped:
			self.ZooKeeper.Client.start_async()


	async def _stop(self):
		def do():
			if not self.ZooKeeper.Stopped:
				self.ZooKeeper.Stopped = True
				self.ZooKeeper.Client.stop()
				self.ZooKeeper.Client.close()

		await self.ProactorService.execute(do)


	def _listener(self, state):
		'''
		Generate PubSub events:

		* ZooKeeperContainer.state/CONNECTED!
		* ZooKeeperContainer.state/LOST!
		* ZooKeeperContainer.state/SUSPENDED!
		'''
		if state == kazoo.protocol.states.KazooState.CONNECTED:
			self.ProactorService.schedule_threadsafe(self._on_connected_at_proactor_thread)
			L.log(LOG_NOTICE, "Connected to ZooKeeper.")
		else:
			if state == kazoo.protocol.states.KazooState.LOST:
				if not self.ZooKeeper.Stopped:
					L.error("ZooKeeper connection LOST. Will try to reconnect.")

			else:
				L.warning("ZooKeeper connection state changed. Zookeeper calls are now blocking!", struct_data={"state": str(state)})

		self.App.PubSub.publish_threadsafe("ZooKeeperContainer.state/{}!".format(state), self)


	def _on_connected_at_proactor_thread(self):
		self.ZooKeeper.Client.ensure_path(self.Path)

		# Re-publish all existing advertisements after connection is established
		if len(self.Advertisments) > 0:
			self._publish_adv_at_proactor_thread()


	def _on_tick300(self, *args):
		# Re-publish all existing advertisements every 300 seconds
		if len(self.Advertisments) > 0:
			self.ProactorService.schedule(self._publish_adv_at_proactor_thread)


	def is_connected(self):
		"""
		Check, if the Zookeeper is connected
		"""
		return self.ZooKeeper.Client.connected


	# Advertisement into Zookeeper

	def advertise(self, data, path):
		if isinstance(data, dict):
			data = json.dumps(data).encode("utf-8")
		elif isinstance(data, str):
			data = data.encode("utf-8")
		assert isinstance(data, bytes)

		full_path = self.Path + path
		existing_adv = self.Advertisments.get(full_path)

		if existing_adv is not None:
			existing_adv.data = data
			existing_adv.version = -1
		else:
			adv = ZooKeeperAdvertisement(path=full_path, data=data)
			self.Advertisments[full_path] = adv

		self.ProactorService.schedule(self._publish_adv_at_proactor_thread)


	def _publish_adv_at_proactor_thread(self):
		if not self.ZooKeeper.Client.connected:
			return

		if not self.AdvertismentsLock.acquire(blocking=False):
			return

		try:

			while True:
				advs = [*self.Advertisments.values()]
				for adv in advs:
					if adv.real_path is not None:
						stats = self.ZooKeeper.Client.exists(adv.real_path)
						if stats is None:
							adv.real_path = None
						else:
							if stats.version != adv.version:
								try:
									stats = self.ZooKeeper.Client.set(adv.real_path, adv.data)
									adv.version = stats.version
								except kazoo.exceptions.NoNodeError:
									adv.real_path = None

					if adv.real_path is None:
						adv.real_path, stats = self.ZooKeeper.Client.create(adv.path, adv.data, sequence=True, ephemeral=True, makepath=True, include_data=True)
						adv.version = stats.version

				if any((adv.version == -1) or (adv.real_path is None) for adv in self.Advertisments.values()) and self.ZooKeeper.Client.connected:
					# Where was a change or a new advertisement, we need to try again
					continue
				else:
					break

		except Exception:
			L.exception("Error when publishing advertisement")

		finally:
			self.AdvertismentsLock.release()


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


@dataclasses.dataclass
class ZooKeeperAdvertisement:
	path: str
	data: bytes
	version: int = -1
	real_path: str = None
