import logging
import json

import aiohttp

from typing import List, Dict, Any, Tuple
import socket
import asyncio

from .. import Service


L = logging.getLogger(__name__)


class DiscoveryService(Service):

	def __init__(self, app, zkc, service_name="asab.DiscoveryService") -> None:
		super().__init__(app, service_name)
		self.ZooKeeperContainer = zkc

	async def locate(self, instance_id: str = None, service_id: str = None) -> list:
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
			in await self._locate(instance_id, service_id)
		]

	async def _locate(self, instance_id: str = None, service_id: str = None) -> List[Tuple]:
		"""
		Locates service instances based on their instance ID or service ID.

		:param instance_id: The unique identifier for a specific instance of a service
		:type instance_id: str
		:param service_id: The ID of the service to locate
		:type service_id: str
		:return: a list of tuples containing the server name and port number of the located service(s).
		"""
		if instance_id is None and service_id is None:
			L.warning("Please provide instance_id, service_id, or appclass to locate the service(s).")
			return

		instances = await self.get_advertised_instances()
		if len(instances) == 0:
			L.warning("No instances available.")
			return
		res = []
		for instance in instances:
			if service_id is not None:
				if service_id != instance.get("service_id", "").lower():
					continue

			if instance_id is not None:
				if instance_id != instance.get("instance_id", "").lower():
					continue

			web = instance.get("web")
			servername = instance.get("servername")
			if web is None or servername is None:
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
				res.append((servername, port))
		return res


	async def get_advertised_instances(self) -> List[Dict]:
		"""
		Returns a list of dictionaries. Each dictionary represents an advertised instance
		obtained by iterating over the items in the `/run` path in ZooKeeper.
		"""
		advertised = []
		async for item, item_data in self._iter_zk_items("/run"):
			data_dict = json.loads(item_data)
			data_dict['zookeeper_id'] = item
			advertised.append(data_dict)

		return advertised


	async def _iter_zk_items(self, path):
		base_path = self.ZooKeeperContainer.Path + path
		items = await self.ZooKeeperContainer.ZooKeeper.get_children(base_path)
		if items is None:
			L.error("Missing '{}/run' folder in ZooKeeper.".format(self.ZooKeeperContainer.Path))
			return

		for item in items:
			item_data = await self.ZooKeeperContainer.ZooKeeper.get_data(base_path + '/' + item)
			yield item, item_data


class DiscoverySession(aiohttp.ClientSession):

	def __init__(self, app):
		self.Session = None
		self.DiscoveryService = app.get_service("asab.DiscoveryService")
		super().__init__(connector=aiohttp.TCPConnector(resolver=DiscoveryResolver(self.DiscoveryService)))



class DiscoveryResolver(aiohttp.DefaultResolver):
	"""Custom aiohttp Resolver for Discovery Session based on default aiohttp resolver."""

	def __init__(self, svc) -> None:
		self._loop = asyncio.get_running_loop()
		self.DiscoveryService = svc


	async def resolve(self, hostname: str, port: int = 0, family: int = socket.AF_INET) -> List[Dict[str, Any]]:
		"""
		Resolves a hostname only with '.asab' domain. and returns a list of dictionaries
		containing information about the resolved hosts further used by aiohttp.TCPConnector

		The hostname to resolve must be in the format of "<value>.<key>.asab",
		where key is "service_id" or "instance_id" and value is the particular identificator of the service to be resolved.
		The "asab" domain is required
		"""
		value, key, domain = hostname.rsplit(".", 3)
		if domain != "asab":
			raise RuntimeError("'asab' domain required. Example url: http://<service>.service_id.asab/asab/v1/config")
		hosts = []
		located_instances = await self.DiscoveryService._locate(**{key: value})
		if located_instances is None or len(located_instances) == 0:
			raise NotDiscoveredError("Failed to discover service '{}'.".format(value))
		for i in located_instances:
			hosts.append(*await super().resolve(i[0], i[1], family))

		return hosts


class NotDiscoveredError(RuntimeError):
	pass
