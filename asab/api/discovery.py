import logging
import json
import socket
import typing
import asyncio

import aiohttp
import kazoo.exceptions

from .. import Service


L = logging.getLogger(__name__)
LogObsolete = logging.getLogger('OBSOLETE')


class DiscoveryService(Service):

	def __init__(self, app, zkc, service_name="asab.DiscoveryService") -> None:
		super().__init__(app, service_name)
		self.ZooKeeperContainer = zkc
		self.ProactorService = zkc.ProactorService
		self.AdvertisedCache = None
		self.CacheLock = asyncio.Lock()
		self.App.PubSub.subscribe("Application.tick/60!", self._on_tick)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)

	def _on_tick(self, msg):
		self._update_cache(msg)

	def _on_zk_ready(self, msg, zkc):
		if zkc == self.ZooKeeperContainer:
			self._update_cache(msg)

	async def locate(self, instance_id: str = None, **kwargs) -> list:
		"""
		Returns a list of URLs for a given instance or service ID.

		:param instance_id: The ID of a specific instance of a service that the client wants to locate.
		:type instance_id: str
		:param service_id: The `service_id` parameter represents identifier of a
		service to locate. It is used to query a service registry to find the
		instances of the service that are currently available.
		:type service_id: str
		:return: A list of URLs in the format "http://servername:port" for the specified instance or
		service.
		"""
		return [
			"http://{}:{}".format(servername, port)
			for servername, port
			in await self._locate(instance_id, **kwargs)
		]

	async def _locate(self, instance_id: str = None, **kwargs) -> typing.Set[typing.Tuple]:
		"""
		Locates service instances based on their identifiers.

		:param instance_id: The unique identifier for a specific instance of a service
		:type instance_id: str
		:return: a list of tuples containing the server name and port number of the located service(s).
		"""
		res = set()

		if instance_id is not None:
			locate_params = {"instance_id": instance_id}
		elif len(kwargs) > 0:
			locate_params = kwargs
		else:
			L.warning("Please provide instance_id, service_id, or other custom id to locate the service(s).")
			return res

		advertised = self.AdvertisedCache
		if len(advertised) == 0:
			L.warning("No instances available.")
			return res

		for id_type, ids in advertised.items():
			if id_type in locate_params:
				if locate_params[id_type] in ids:
					res = res | ids[locate_params[id_type]]

		return res

	def discover(self) -> typing.Dict[str, typing.Dict[str, typing.Set[typing.Tuple[str, int]]]]:
		return self.AdvertisedCache

	async def get_advertised_instances(self) -> typing.List[typing.Dict]:
		"""
		This method is here for backward compatibility. Use `discover()` method instead.
		Returns a list of dictionaries. Each dictionary represents an advertised instance
		obtained by iterating over the items in the `/run` path in ZooKeeper.
		"""
		LogObsolete.warning("This method is obsolete. Use `discover()` method instead.")
		advertised = []
		async for item, item_data in self._iter_zk_items("/run"):
			item_data['zookeeper_id'] = item
			advertised.append(item_data)

		return advertised

	async def _get_advertised_instances(self):
		"""
		Returns structured dataset of identifier types, identifiers of instances and hosts and ports where they can be found.
		It is a dict of identifier types as keys and dict as values. The second-layer dict has identifiers as keys an a set of tuples as a value. Each tuple contains host and port.

		Example of the data structure:
			{
				"instance_id": {
					"lmio-receiver-1": {("node1", 1234)},
					"asab-remote-control-1": {("node2", 1234)}
					...
				},
				"service_id": {
					"lmio-receiver": {("node1", 1234), ("node2", 1234), ("node3", 1234)},
					...
				},
				"custom1_id": {
					"myid123": {("node1", 5678), ("node2", 5678)},
					...
				},
				"custom2_id": {
					"myid123": {("node1", 5678), ("node2", 5678)},
					...
				},
				...
			}
		"""
		if self.CacheLock.locked():
			# Only one cache update at a time
			return

		async with self.CacheLock:

			advertised = {
				"instance_id": {},
				"service_id": {},
			}
			async for item, item_data in self._iter_zk_items("/run"):
				instance_id = item_data.get("instance_id")
				service_id = item_data.get("service_id")
				discovery: typing.Dict[str, list] = item_data.get("discovery", {})

				if instance_id is not None:
					discovery["instance_id"] = [instance_id]

				if instance_id is not None:
					discovery["service_id"] = [service_id]

				web = item_data.get("web")
				host = item_data.get("node_id", item_data.get("host"))

				if web is None or host is None:
					continue
				for i in web:
					try:
						ip = i[0]
						port = i[1]
					except KeyError:
						L.error("Unexpected format of 'web' section in advertised data: '{}'".format(web))
						return
					if ip not in ("0.0.0.0", "::"):
						continue

					if discovery is not None:
						for id_type, ids in discovery.items():
							if advertised.get(id_type) is None:
								advertised[id_type] = {}
							for identifier in ids:
								if identifier is not None:
									if advertised[id_type].get(identifier) is None:
										advertised[id_type][identifier] = {(host, port)}
									else:
										advertised[id_type][identifier].add((host, port))

			self.AdvertisedCache = advertised


	async def _iter_zk_items(self, path):
		base_path = self.ZooKeeperContainer.Path + path

		def get_items():
			try:
				return self.ZooKeeperContainer.ZooKeeper.Client.get_children(base_path, watch=self._update_cache)
			except (kazoo.exceptions.SessionExpiredError, kazoo.exceptions.ConnectionLoss):
				# TODO: this is silent error
				return None

		def get_data(item):
			try:
				data, stat = self.ZooKeeperContainer.ZooKeeper.Client.get((base_path + '/' + item), watch=self._update_cache)
				return data
			except (kazoo.exceptions.SessionExpiredError, kazoo.exceptions.ConnectionLoss):
				# TODO: this is silent error
				return None

		items = await self.ProactorService.execute(get_items)
		if items is None:
			L.error("Missing '{}/run' folder in ZooKeeper.".format(self.ZooKeeperContainer.Path))
			return

		for item in items:
			item_data = await self.ProactorService.execute(get_data, item)
			if item_data is None:
				continue
			yield item, json.loads(item_data)


	def session(self, base_url=None, **kwargs) -> aiohttp.ClientSession:
		'''
		Usage:

		async with self.DiscoveryService.session() as session:
			# use URL in format: <protocol>://<value>.<key>.asab/<endpoint> where key is "service_id" or "instance_id" and value the respective serivce identificator
			async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
				...
		'''
		return aiohttp.ClientSession(base_url, connector=aiohttp.TCPConnector(resolver=DiscoveryResolver(self)), **kwargs)


	def _update_cache(self, watched_event):
		# TODO: update just parts of the cache based on the watched_event parameter to be more efficient
		self.App.TaskService.schedule(self._get_advertised_instances())


class DiscoveryResolver(aiohttp.DefaultResolver):
	"""Custom aiohttp Resolver for Discovery Session based on default aiohttp resolver."""

	def __init__(self, svc) -> None:
		super().__init__()
		self.DiscoveryService = svc


	async def resolve(self, hostname: str, port: int = 0, family: int = socket.AF_INET) -> typing.List[typing.Dict[str, typing.Any]]:
		"""
		Resolves a hostname only with '.asab' domain. and returns a list of dictionaries
		containing information about the resolved hosts further used by aiohttp.TCPConnector

		The hostname to resolve must be in the format of "<value>.<key>.asab",
		where key is "service_id" or "instance_id" and value is the particular identificator of the service to be resolved.
		The "asab" domain is required for resolution, otherwise it is treated like normal URL.
		"""
		url_split = hostname.rsplit(".", 2)

		# If there is no asab domain, it is normal URL and resolve it normally
		if url_split[-1] != "asab":
			return await super().resolve(hostname, port, family)

		# Make sure the format of the hostname is right
		if len(url_split) != 3:
			raise NotDiscoveredError("Invalid format of the hostname '{}'. Use e.g. `asab-config.service_id.asab` instead.".format(hostname))

		hosts = []
		located_instances = await self.DiscoveryService._locate(**{url_split[1]: url_split[0]})
		if located_instances is None or len(located_instances) == 0:
			raise NotDiscoveredError("Failed to discover '{}'.".format(hostname))
		for i in located_instances:
			hosts.append(*await super().resolve(i[0], i[1], family))

		return hosts


class NotDiscoveredError(RuntimeError):
	pass
