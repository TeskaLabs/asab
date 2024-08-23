import datetime
import json
import copy
import socket
import typing
import asyncio
import logging
import os

import aiohttp
import kazoo.exceptions

try:
	# Optional dependency for using internal authorization
	import jwcrypto
	import jwcrypto.jwt
	import jwcrypto.jwk
except ModuleNotFoundError:
	jwcrypto = None

from .. import Service


L = logging.getLogger(__name__)
LogObsolete = logging.getLogger('OBSOLETE')


class DiscoveryService(Service):
	"""
	Service for discovering ASAB microservices in a server cluster. It is based on searching in ZooKeeper `/run` path.
	"""
	def __init__(self, app, zkc, service_name="asab.DiscoveryService") -> None:
		super().__init__(app, service_name)
		self.ZooKeeperContainer = zkc
		self.ProactorService = zkc.ProactorService
		self.InternalAuthKeyPath = "/asab/auth/internal_auth_private.key"
		self.InternalAuthKey = None
		self.InternalAuthToken = None
		self.InternalAuthTokenExpiration: datetime.timedelta = datetime.timedelta(seconds=5 * 300)

		self._advertised_cache = dict()
		self._cache_lock = asyncio.Lock()
		self._ready_event = asyncio.Event()

		self.App.PubSub.subscribe("Application.tick/300!", self._on_tick)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)



	def _on_tick(self, msg):
		self.App.TaskService.schedule(self._rescan_advertised_instances())
		if jwcrypto is not None:
			self._ensure_internal_auth_token()


	def _on_zk_ready(self, msg, zkc):
		if zkc == self.ZooKeeperContainer:
			self.App.TaskService.schedule(self._rescan_advertised_instances())
			if jwcrypto is not None:
				self.App.TaskService.schedule(self._ensure_internal_auth_key(zkc))


	async def _ensure_internal_auth_key(self, zkc=None):
		zkc = zkc or self.ZooKeeperContainer
		private_key_json = None
		# Attempt to create and write a new private key
		# while avoiding race condition with other ASAB services
		while not private_key_json:
			# Try to get the key
			try:
				private_key_json, _ = zkc.ZooKeeper.Client.get(self.InternalAuthKeyPath)
				break
			except kazoo.exceptions.NoNodeError:
				pass

			# Generate a new key
			private_key = jwcrypto.jwk.JWK.generate(kty="EC", crv="P-256")
			private_key_json = json.dumps(private_key.export(as_dict=True)).encode("utf-8")
			try:
				zkc.ZooKeeper.Client.create(self.InternalAuthKeyPath, private_key_json, makepath=True)
				L.info("Internal auth key created.", struct_data={
					"kid": private_key.key_id, "path": self.InternalAuthKeyPath})
			except kazoo.exceptions.NodeExistsError:
				# Another ASAB service has probably created the key in the meantime
				pass

		private_key = jwcrypto.jwk.JWK.from_json(private_key_json)
		if private_key != self.InternalAuthKey:
			# Private key has changed
			self.InternalAuthKey = private_key
			self._ensure_internal_auth_token(force_new=True)


	def _ensure_internal_auth_token(self, force_new: bool = False):
		assert self.InternalAuthKey

		def _get_own_discovery_url():
			instance_id = os.getenv("INSTANCE_ID", None)
			if instance_id:
				return "http://{}.instance_id.asab".format(instance_id)

			service_id = os.getenv("SERVICE_ID", None)
			if service_id:
				return "http://{}.service_id.asab".format(service_id)

			return "http://{}".format(self.App.HostName)

		if self.InternalAuthToken and not force_new:
			claims = json.loads(self.InternalAuthToken.claims)
			if claims.get("exp") > (
				datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=300)
			).timestamp():
				# Token is valid and does not expire soon
				return

		# Use this service's discovery URL as issuer ID and authorized party ID
		my_discovery_url = _get_own_discovery_url()
		expiration = datetime.datetime.now(datetime.timezone.utc) + self.InternalAuthTokenExpiration
		claims = {
			# Issuer (URL of the app that created the token)
			"iss": my_discovery_url,
			# Issued at
			"iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
			# Expires at
			"exp": int((expiration).timestamp()),
			# Authorized party
			"azp": my_discovery_url,
			# Audience (who is allowed to use this token)
			"aud": "http://{}".format(self.App.HostName),  # TODO: Something that signifies "anyone in this internal space"
			# Tenants and resources
			"resources": {
				"*": ["authz:superuser"],
			}
		}

		self.InternalAuthToken = jwcrypto.jwt.JWT(
			header={
				"alg": "ES256",
				"typ": "JWT",
				"kid": self.InternalAuthKey.key_id,
			},
			claims=json.dumps(claims)
		)
		self.InternalAuthToken.make_signed_token(self.InternalAuthKey)

		L.info("New internal auth token issued.", struct_data={"exp": expiration})


	async def locate(self, instance_id: str = None, **kwargs) -> set:
		"""
		Return a list of URLs for a given instance or service ID.

		Args:
			instance_id (str): The ID of a specific instance of a service that the client wants to locate.
			service_id (str): The `service_id` parameter represents identifier of a service to locate.
				It is used to query a service registry to find the instances of the service that are currently available.

		Returns: A list of URLs in the format "http://servername:port" for the specified instance or service.
		"""

		if instance_id is not None:
			locate_params = {"instance_id": instance_id}

		elif len(kwargs) > 0:
			locate_params = kwargs

		else:
			L.warning("Please provide instance_id, service_id, or other custom id to locate the service(s).")
			return None

		# Each taget can have two records - one for ipv4 and second for ipv6. This information is redundant in the URL format.
		return set([
			"http://{}:{}".format(servername, port)
			for servername, port, family
			in await self._locate(locate_params)
		])

	async def _locate(self, locate_params) -> typing.Set[typing.Tuple]:
		"""
		Locate service instances based on their instance ID or service ID.

		Args:
			instance_id (str): The unique identifier for a specific instance of a service
			service_id (str): The ID of the service to locate

		Returns: a list of tuples containing the server name and port number of the located service(s).
		"""
		res = set()

		await asyncio.wait_for(self._ready_event.wait(), 600)

		if len(self._advertised_cache) == 0:
			L.warning("No instances to discover. Make sure [zookeeper] configuration is identical for all the ASAB services in the cluster.")
			return res

		for id_type, ids in self._advertised_cache.items():
			if id_type in locate_params:
				if locate_params[id_type] in ids:
					res = res | ids[locate_params[id_type]]

		return res


	async def discover(self) -> typing.Dict[str, typing.Dict[str, typing.Set[typing.Tuple]]]:
		# We need to make a copy of the cache so that the caller can't modify our cache.
		await asyncio.wait_for(self._ready_event.wait(), 600)
		return copy.deepcopy(self._advertised_cache)


	async def get_advertised_instances(self) -> typing.List[typing.Dict]:
		"""
		This method is here for backward compatibility. Use `discover()` method instead.
		Returns a list of dictionaries. Each dictionary represents an advertised instance
		obtained by iterating over the items in the `/run` path in ZooKeeper.
		"""
		LogObsolete.warning("The method 'get_advertised_instances()' in DiscoveryService is obsolete. Use `discover()` method instead.")
		advertised = []
		async for item, item_data in self._iter_zk_items():
			item_data['ephemeral_id'] = item
			advertised.append(item_data)

		return advertised


	async def _rescan_advertised_instances(self):
		"""
		Returns structured dataset of identifier types, identifiers of instances and hosts and ports where they can be found.
		It is a dict of identifier types as keys and dict as values. The second-layer dict has identifiers as keys an a set of tuples as a value. Each tuple contains host and port.

		Example of the data structure:
			{
				"instance_id": {
					"lmio-receiver-1": {("node1", 1234, socket.AF_INET)},
					"asab-remote-control-1": {("node2", 1234, socket.AF_INET6)}
					...
				},
				"service_id": {
					"lmio-receiver": {("node1", 1234, socket.AF_INET), ("node2", 1234, socket.AF_INET), ("node3", 1234, socket.AF_INET)},
					...
				},
				"custom1_id": {
					"myid123": {("node1", 5678, socket.AF_INET), ("node2", 5678, socket.AF_INET6)},
					...
				},
				"custom2_id": {
					"myid123": {("node1", 5678, socket.AF_INET), ("node2", 5678, socket.AF_INET)},
					...
				},
				...
			}
		"""
		if self._cache_lock.locked():
			# Only one rescan / cache update at a time
			return

		async with self._cache_lock:

			advertised = {
				"instance_id": {},
				"service_id": {},
			}

			iterator = self._iter_zk_items()
			if iterator is None:
				return  # reason logged from the _iter_zk_items method

			async for item, item_data in iterator:
				instance_id = item_data.get("instance_id")
				service_id = item_data.get("service_id")
				discovery: typing.Dict[str, list] = item_data.get("discovery", {})

				if instance_id is not None:
					discovery["instance_id"] = [instance_id]

				if instance_id is not None:
					discovery["service_id"] = [service_id]

				host = item_data.get("host")
				if host is None:
					continue

				web = item_data.get("web")
				if web is None:
					continue

				for i in web:

					try:
						ip = i[0]
						port = i[1]
					except KeyError:
						L.error("Unexpected format of 'web' section in advertised data: '{}'".format(web))
						return

					if ip == "0.0.0.0":
						family = socket.AF_INET
					elif ip == "::":
						family = socket.AF_INET6
					else:
						continue

					if discovery is not None:
						for id_type, ids in discovery.items():
							if advertised.get(id_type) is None:
								advertised[id_type] = {}

							for identifier in ids:
								if identifier is not None:
									if advertised[id_type].get(identifier) is None:
										advertised[id_type][identifier] = {(host, port, family)}
									else:
										advertised[id_type][identifier].add((host, port, family))

			self._advertised_cache = advertised
			self._ready_event.set()


	async def _iter_zk_items(self):
		base_path = self.ZooKeeperContainer.Path + "/run"

		def get_items():
			try:
				# Create the base path if it does not exist
				if not self.ZooKeeperContainer.ZooKeeper.Client.exists(base_path):
					self.ZooKeeperContainer.ZooKeeper.Client.create(base_path, b'', makepath=True)

				return self.ZooKeeperContainer.ZooKeeper.Client.get_children(base_path, watch=self._on_change_threadsafe)
			except (kazoo.exceptions.SessionExpiredError, kazoo.exceptions.ConnectionLoss):
				L.warning("Connection to ZooKeeper lost. Discovery Service could not fetch up-to-date state of the cluster services.")
				return None

			except kazoo.exceptions.KazooException:
				return None

		def get_data(item):
			try:
				data, stat = self.ZooKeeperContainer.ZooKeeper.Client.get((base_path + '/' + item), watch=self._on_change_threadsafe)
				return data
			except (kazoo.exceptions.SessionExpiredError, kazoo.exceptions.ConnectionLoss):
				L.warning("Connection to ZooKeeper lost. Discovery Service could not fetch up-to-date state of the cluster services.")
				return None

			except kazoo.exceptions.KazooException:
				# There's a race condition -> if ZK node is deleted between get_items and get_data calls, NoNodeError is raised. Let's just ignore it. The ZK node is already deleted.
				return None

		items = await self.ProactorService.execute(get_items)
		if items is None:
			return

		for item in items:
			item_data = await self.ProactorService.execute(get_data, item)
			if item_data is None:
				continue
			yield item, json.loads(item_data)

	def _on_change_threadsafe(self, watched_event):
		# Runs on a thread, returns the process back to the main thread
		def _update_cache():
			self.App.TaskService.schedule(self._rescan_advertised_instances())
		self.App.Loop.call_soon_threadsafe(_update_cache)


	def session(self, base_url=None, auth=None, headers=None, **kwargs) -> aiohttp.ClientSession:
		"""
		Usage:

		```python
		async with self.DiscoveryService.session() as session:
			# use URL in format: <protocol>://<value>.<key>.asab/<endpoint>
			# where key is "service_id" or "instance_id"
			# and value the respective service identificator
			async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
				...

		# Using end-user authorization (from the UI)
		async with self.DiscoveryService.session(auth=request) as session:
			async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
				...

		# Using internal m2m authorization
		async with self.DiscoveryService.session(auth="internal") as session:
			async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
				...
		"""
		if isinstance(auth, aiohttp.ClientRequest):
			if headers is None:
				headers = {}
			assert "Authorization" in auth.headers
			headers["Authorization"] = auth.headers.get("Authorization")
		elif auth == "internal":
			if jwcrypto is None:
				raise ModuleNotFoundError(
					"You are trying to use internal auth without 'jwcrypto' installed. "
					"Please run 'pip install jwcrypto' or install asab with 'authz' optional dependency."
				)
			if headers is None:
				headers = {}
			headers["Authorization"] = "Bearer {}".format(self.InternalAuthToken.serialize())
		elif auth is None:
			pass
		else:
			raise ValueError(
				"Invalid 'auth' value. "
				"Only instances of aiohttp.ClientRequest or the literal string 'internal' are allowed. "
				"Found {}.".format(type(auth))
			)
		return aiohttp.ClientSession(
			base_url,
			connector=aiohttp.TCPConnector(resolver=DiscoveryResolver(self)),
			headers=headers,
			**kwargs
		)


class DiscoveryResolver(aiohttp.DefaultResolver):
	"""
	Custom resolver for Discovery Session based on default `aiohttp` resolver.
	"""

	def __init__(self, svc) -> None:
		super().__init__()
		self.DiscoveryService = svc


	async def resolve(self, hostname: str, port: int = 0, family: int = socket.AF_INET) -> typing.List[typing.Dict[str, typing.Any]]:
		"""
		Resolve a hostname only with '.asab' domain. and return a list of dictionaries
		containing information about the resolved hosts further used by `aiohttp.TCPConnector`.

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
		located_instances = await self.DiscoveryService._locate({url_split[1]: url_split[0]})
		if located_instances is None or len(located_instances) == 0:
			raise NotDiscoveredError("Failed to discover '{}'.".format(hostname))

		for phostname, pport, pfamily in located_instances:
			try:
				resolved = await super().resolve(phostname, pport, pfamily)
			except socket.gaierror:
				# Skip unresolved hosts
				continue
			hosts.extend(resolved)

		if len(hosts) == 0:
			raise NotDiscoveredError("Failed to resolve any of the hosts for '{}'.".format(hostname))

		return hosts


class NotDiscoveredError(RuntimeError):
	"""
	Raised when given service is not discovered.
	"""
	pass
