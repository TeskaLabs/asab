import io
import hashlib
import typing
import logging
import functools
import os.path
import urllib.parse

import kazoo.exceptions
import kazoo.recipe.watchers

from .abc import LibraryProviderABC
from ..item import LibraryItem
from ...zookeeper import ZooKeeperContainer
from ...contextvars import Tenant, Authz

#

L = logging.getLogger(__name__)

#


class ZooKeeperLibraryProvider(LibraryProviderABC):

	"""

	Configuration variant:


	1) ZooKeeper provider is fully configured from [zookeeper] section

	.. code::

		[zookeeper]
		servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
		path=/library

		[library]
		providers:
			zk://



	2) ZooKeeper provider is configured by `servers` from [zookeeper] section and path from URL

	Path will be `/library`.

	.. code::

		[zookeeper]
		servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
		path=/else

		[library]
		providers:
			zk:///library


	2.1) ZooKeeper provider is configured by `servers` from [zookeeper] section and path from URL

	Path will be `/`, this is a special case to 2)

	.. code::

		[zookeeper]
		servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
		path=/else

		[library]
		providers:
			zk:///

	3) ZooKeeper provider is fully configured from URL

	.. code::

		[library]
		providers:
			zk://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/library


	4) ZooKeeper provider is configured by `servers` from [zookeeper] section and  joined `path` from [zookeeper] and
	path from URL

	Path will be `/else/library`

	.. code::

		[zookeeper]
		servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
		path=/else

		[library]
		providers:
			zk://./library


	If `path` from [zookeeper] section is missing, an application class name will be used
	Ex. `/BSQueryApp/library`

	Usage of asab.contextvars.Tenant:
		The 'Tenant' context variable is used to specify the current tenant context.
		It can be set at the beginning of an operation (e.g., a web request) to ensure that all
		subsequent operations within that context are executed under the specified tenant.
		The context variable is reset to its default value (None) at the end of the operation.

	Example:

		# Import tenant context variable
		import asab.contextvars

		# Set your working tenant
		tenant_token = asab.contextvars.Tenant.set('default')

		# Use try-finally flow to ensure the context is always properly reset
		try:
			# Perform library operation in the selected tenant
			LibraryService.read("asab/library/schema.json")
		finally:
			# Reset the tenant context
			asab.contextvars.Tenant.reset(tenant_token)

	"""

	def __init__(self, library, path, layer):
		super().__init__(library, layer)

		url_pieces = urllib.parse.urlparse(path)

		self.FullPath = url_pieces.scheme + '://'
		self.BasePath = url_pieces.path.lstrip("/")
		while self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]
		self.BasePath = '/' + self.BasePath
		if self.BasePath == '/':
			self.BasePath = ''

		if url_pieces.netloc in ["", "."]:
			# if netloc is not provided `zk:///path`, then use `zookeeper` section from config
			config_section_name = 'zookeeper'
			z_url = None
		else:
			config_section_name = ''
			z_url = path

		# Initialize ZooKeeper client
		zksvc = self.App.get_service("asab.ZooKeeperService")
		self.ZookeeperContainer = ZooKeeperContainer(
			zksvc,
			config_section_name=config_section_name,
			z_path=z_url
		)
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper

		if config_section_name == 'zookeeper':
			self.FullPath += self.ZookeeperContainer.Config['servers']
		else:
			self.FullPath += url_pieces.netloc

		# Handle `zk://` configuration
		if z_url is None and url_pieces.netloc == "" and url_pieces.path == "" and self.ZookeeperContainer.Path != '':
			self.BasePath = '/' + self.ZookeeperContainer.Path

		# Handle `zk://./path` configuration
		if z_url is None and url_pieces.netloc == "." and self.ZookeeperContainer.Path != '':
			self.BasePath = '/' + self.ZookeeperContainer.Path + self.BasePath

		self.FullPath += self.BasePath

		self.VersionNodePath = self.build_path('/.version.yaml')
		self.Version = None  # Will be read when a library become ready
		self.VersionWatch = None

		self.DisabledNodePath = self.build_path('/.disabled.yaml')
		self.DisabledWatch = None

		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_connected)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/SUSPENDED!", self._on_zk_lost)
		self.App.PubSub.subscribe("Application.tick/60!", self._get_version_counter)

		# This is a contingency check for changes for subscribed folders in library even without version counter change.
		self.App.PubSub.subscribe("Application.tick/600!", self._on_library_changed)

		self.Subscriptions: typing.Set[typing.Tuple[typing.Union[str, tuple, None], str]] = set()
		self.NodeDigests: typing.Dict[str, bytes] = {}
		self.SubscriptionActualPaths: typing.Dict[typing.Tuple[typing.Union[str, tuple, None], str], typing.List[str]] = {}
		self.SubscriptionDescriptors: typing.Dict[
			typing.Tuple[typing.Union[str, tuple, None], str],
			typing.List[typing.Dict[str, typing.Any]],
		] = {}
		self.WatchSubscriptions: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]] = {}
		self.PersistentWatches: typing.Set[str] = set()
		self.AggrTimer = Timer(self.App, self._on_aggr_timer)
		self.AggrEvents: typing.Set[str] = set()


	async def finalize(self, app):
		"""
		The `finalize` function is called when the application is shutting down
		"""
		await self._remove_subscription_watches()
		self.DisabledWatch = None
		self.AggrTimer.stop()
		self.AggrEvents.clear()
		self.PersistentWatches = set()
		self.WatchSubscriptions = {}
		self.SubscriptionActualPaths = {}
		self.SubscriptionDescriptors = {}
		zksvc = self.App.get_service("asab.ZooKeeperService")
		await zksvc.remove(self.ZookeeperContainer)


	async def _on_zk_connected(self, event_name, zkcontainer):
		"""
		When the Zookeeper container is connected, set the self.Zookeeper property to the Zookeeper object.
		"""
		if zkcontainer != self.ZookeeperContainer:
			return

		L.info("is connected.", struct_data={'path': self.FullPath})

		def on_version_changed(version, event):
			self.App.Loop.call_soon_threadsafe(self._check_version_counter, version)

		def install_watcher():
			return kazoo.recipe.watchers.DataWatch(self.Zookeeper.Client, self.VersionNodePath, on_version_changed)

		self.VersionWatch = await self.Zookeeper.ProactorService.execute(install_watcher)

		def on_disabled_changed(data, stat):
			# Whenever .disabled.yaml changes, reload disables
			self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

		def install_disabled_watcher():
			return kazoo.recipe.watchers.DataWatch(self.Zookeeper.Client, self.DisabledNodePath, on_disabled_changed)

		self.DisabledWatch = await self.Zookeeper.ProactorService.execute(install_disabled_watcher)

		if len(self.WatchSubscriptions) > 0:
			await self._restore_subscription_watches()

		await self._set_ready()


	async def _on_zk_lost(self, event_name, zkcontainer):
		if zkcontainer != self.ZookeeperContainer:
			return

		await self._set_ready(ready=False)


	async def _get_version_counter(self, event_name=None):
		if self.Zookeeper is None or not self.IsReady:
			return

		try:
			version = await self.Zookeeper.get_data(self.VersionNodePath)
		except kazoo.exceptions.ConnectionClosedError:
			return

		self._check_version_counter(version)


	def _check_version_counter(self, version):
		# If version is `None` aka `/.version.yaml` doesn't exists, then assume version -1
		if version is not None:
			try:
				version = int(version)
			except ValueError:
				version = 1
		else:
			version = 1

		if self.Version is None:
			# Initial grab of the version
			self.Version = version
			return

		if self.Version == version:
			# The version has not changed
			return

		self.App.TaskService.schedule(self._on_library_changed())

	# inside class ZooKeeperLibraryProvider

	def _current_tenant_id(self):
		try:
			return Tenant.get()
		except LookupError:
			return None

	def _current_credentials_id(self):
		"""
		Return current CredentialsId from auth context, or None if not present.
		"""
		try:
			authz = Authz.get()
			return getattr(authz, "CredentialsId", None)
		except LookupError:
			return None

	def _personal_node_path(self, path: str, tenant_id: typing.Optional[str], cred_id: typing.Optional[str]) -> typing.Optional[str]:
		"""
		Returns '/.personal/{tenant}/{cred}{path}' or None if tenant/cred are missing.
		"""
		assert path[:1] == '/'
		if not tenant_id or not cred_id:
			return None
		return "{}/.personal/{}/{}{}".format(self.BasePath, tenant_id, cred_id, path).rstrip("/")

	def _subscription_personal_path(self, path: str, target: typing.Union[str, tuple, None]) -> typing.Optional[str]:
		tenant_id = self._current_tenant_id()
		if isinstance(target, tuple) and len(target) == 2 and target[0] == "personal":
			cred_id = target[1]
		else:
			cred_id = self._current_credentials_id()
		if not tenant_id or not cred_id:
			return None
		return "/.personal/{}/{}{}".format(tenant_id, cred_id, path)

	@staticmethod
	def _normalize_subscription_path(path: str) -> str:
		assert path[:1] == '/'
		if path != '/':
			path = path.rstrip('/')
			if path == '':
				return '/'
		return path

	def _zk_node_path(self, path: str) -> str:
		path = self._normalize_subscription_path(path)
		if self.BasePath == '':
			return path
		if path == '/':
			return self.BasePath
		return "{}{}".format(self.BasePath, path)

	def _persistent_recursive_watch_mode(self):
		add_watch_mode = getattr(kazoo.protocol.states, "AddWatchMode", None)
		mode = getattr(add_watch_mode, "PERSISTENT_RECURSIVE", None) if add_watch_mode is not None else None
		if mode is None or not hasattr(self.Zookeeper.Client, "add_watch"):
			raise RuntimeError(
				"ZooKeeper subscriptions require vendored kazoo with persistent recursive watch support."
			)
		return mode

	def _watcher_type_any(self):
		watcher_type = getattr(kazoo.protocol.states, "WatcherType", None)
		return getattr(watcher_type, "ANY", None) if watcher_type is not None else None

	async def read(self, path: str) -> typing.Optional[typing.IO]:
		if self.Zookeeper is None:
			L.warning(
				"ZooKeeper library provider is not connected yet; read operation rejected.",
				struct_data={"path": path},
			)
			raise RuntimeError("Zookeeper Client has not been established (yet). Not ready.")

		# Build candidates in precedence order
		candidate_paths: typing.List[str] = []

		# personal (needs both tenant + CredentialsId)
		try:
			tenant_id = Tenant.get()
		except LookupError:
			tenant_id = None

		try:
			authz = Authz.get()
			cred_id = getattr(authz, "CredentialsId", None)
		except LookupError:
			cred_id = None

		personal_candidate = self._personal_node_path(path, tenant_id, cred_id)
		if personal_candidate:
			candidate_paths.append(personal_candidate)

		# tenant
		tenant_candidate = self.build_path(path, tenant_specific=True)
		if tenant_candidate not in candidate_paths:
			candidate_paths.append(tenant_candidate)

		# global
		global_candidate = self.build_path(path, tenant_specific=False)
		if global_candidate not in candidate_paths:
			candidate_paths.append(global_candidate)

		try:
			for node_path in candidate_paths:
				node_data = await self.Zookeeper.get_data(node_path)
				if node_data is not None:
					return io.BytesIO(initial_bytes=node_data)
			return None

		except kazoo.exceptions.ConnectionClosedError:
			L.warning(
				"ZooKeeper library provider lost connection; operation rejected until reconnected.",
			)
			raise RuntimeError("Zookeeper library provider is not ready") from None

	async def list(self, path: str) -> list:
		if self.Zookeeper is None:
			L.warning(
				"ZooKeeper library provider is not connected yet; list operation rejected.",
				struct_data={"path": path},
			)
			raise RuntimeError("Zookeeper Client has not been established (yet). Not ready.")

		# global
		global_node_path = self.build_path(path, tenant_specific=False)
		global_nodes = await self.Zookeeper.get_children(global_node_path) or []
		global_items = await self.process_nodes(global_nodes, path, target="global")

		# tenant
		tenant_node_path = self.build_path(path, tenant_specific=True)
		if tenant_node_path != global_node_path:
			tenant_nodes = await self.Zookeeper.get_children(tenant_node_path) or []
			tenant_items = await self.process_nodes(tenant_nodes, path, target="tenant")
		else:
			tenant_items = []

		# personal (only for current tenant + current credentials)
		try:
			tenant_id = Tenant.get()
		except LookupError:
			tenant_id = None

		try:
			authz = Authz.get()
			cred_id = getattr(authz, "CredentialsId", None)
		except LookupError:
			cred_id = None

		personal_items = []
		if tenant_id and cred_id:
			personal_node_path = "{}/.personal/{}/{}{}".format(self.BasePath, tenant_id, cred_id, path)
			personal_node_path = personal_node_path.replace("//", "/")
			try:
				personal_nodes = await self.Zookeeper.get_children(personal_node_path) or []
			except kazoo.exceptions.NoNodeError:
				personal_nodes = []
			personal_items = await self.process_nodes(personal_nodes, path, target="personal")

		# precedence in listing result: personal + tenant + global (no name merge here)
		return personal_items + tenant_items + global_items

	async def process_nodes(self, nodes, base_path, target="global"):
		items = []
		for node in nodes:
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), node.split(os.path.sep), False)
			if startswithdot:
				continue

			if '.' in node and not node.endswith(('.io', '.d')):
				fname = "{}/{}".format(base_path.rstrip("/"), node)
				ftype = "item"
				try:
					if target == "personal":
						# current tenant + current cred
						try:
							tenant_id = Tenant.get()
						except LookupError:
							tenant_id = None
						try:
							authz = Authz.get()
							cred_id = getattr(authz, "CredentialsId", None)
						except LookupError:
							cred_id = None
						node_path = self._personal_node_path(fname, tenant_id, cred_id) or ""
					else:
						node_path = self.build_path(fname, tenant_specific=(target == "tenant"))
					zstat = await self.Zookeeper.exists(node_path) if node_path else None
					size = zstat.dataLength if zstat else 0
				except kazoo.exceptions.NoNodeError:
					size = None
				except Exception as e:
					L.warning(
						"Failed to read ZooKeeper node size for library item.",
						struct_data={"path": fname, "error": str(e)},
					)
					size = None
			else:
				fname = "{}/{}/".format(base_path.rstrip("/"), node)
				ftype = "dir"
				size = None

			if self.Layer == 0:
				if target == "global":
					layer_label = "0:global"
				elif target == "tenant":
					layer_label = "0:tenant"
				elif target == "personal":
					layer_label = "0:personal"
				else:
					layer_label = "0:{}".format(target)
			else:
				layer_label = self.Layer

			items.append(LibraryItem(
				name=fname,
				type=ftype,
				layers=[layer_label],
				providers=[self],
				size=size
			))
		return items

	def build_path(self, path, tenant_specific=False):
		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		if tenant_specific:
			try:
				tenant = Tenant.get()
			except LookupError:
				tenant = None

			if tenant:
				node_path = self.BasePath + '/.tenants/' + tenant + path

		node_path = node_path.rstrip("/")

		assert '//' not in node_path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"
		assert node_path[0] == '/', "Directory path must start with a forward slash (/). For example: /library/Templates/"

		return node_path

	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		key = (target, path)
		self.Subscriptions.add(key)
		if not hasattr(self, "SubscriptionActualPaths"):
			self.SubscriptionActualPaths = {}
		if key in self.SubscriptionDescriptors:
			return

		if target in {None, "global"}:
			self.SubscriptionActualPaths[key] = [path]
			self.NodeDigests[path] = await self._get_directory_hash(path)

		elif target == "tenant":
			actual_paths = []
			for tenant in await self._get_tenants():
				actual_path = "/.tenants/{}{}".format(tenant, path)
				actual_paths.append(actual_path)
				self.NodeDigests[actual_path] = await self._get_directory_hash(actual_path)
			self.SubscriptionActualPaths[key] = actual_paths

		elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			_, tenant = target
			actual_path = "/.tenants/{}{}".format(tenant, path)
			self.SubscriptionActualPaths[key] = [actual_path]
			self.NodeDigests[actual_path] = await self._get_directory_hash(actual_path)

		elif target == "personal" or (isinstance(target, tuple) and len(target) == 2 and target[0] == "personal"):
			actual_path = self._subscription_personal_path(path, target)
			if actual_path is not None:
				self.SubscriptionActualPaths[key] = [actual_path]
				self.NodeDigests[actual_path] = await self._get_directory_hash(actual_path)
			else:
				self.SubscriptionActualPaths[key] = []
		else:
			raise ValueError("Unexpected target: {!r}".format(target))

		self._persistent_recursive_watch_mode()
		descriptors = []
		for actual_path in self.SubscriptionActualPaths[key]:
			actual_path = self._normalize_subscription_path(actual_path)
			if not await self._subscription_path_exists(actual_path):
				continue
			descriptor = self._build_subscription_descriptor(target, path, actual_path)
			descriptors.append(descriptor)
			self._attach_watch_subscription(descriptor)
			await self._ensure_subscription_watch(descriptor["zk_path"])
		self.SubscriptionDescriptors[key] = descriptors

	async def _get_directory_hash(self, path):
		path = self.BasePath + path

		def recursive_traversal(path, digest):
			if not self.Zookeeper.Client.exists(path):
				return

			children = self.Zookeeper.Client.get_children(path)
			for child in children:
				if path != "/":
					child_path = "{}/{}".format(path, child)
				else:
					child_path = "/{}".format(child)
				zstat = self.Zookeeper.Client.exists(child_path)
				digest.update("{}\n{}\n".format(child_path, zstat.version).encode('utf-8'))
				recursive_traversal(child_path, digest)

		digest = hashlib.sha1()
		await self.Zookeeper.ProactorService.execute(recursive_traversal, path, digest)
		return digest.digest()

	async def _subscription_path_exists(self, actual_path: str) -> bool:
		return (await self.Zookeeper.exists(self._zk_node_path(actual_path))) is not None

	def _build_subscription_descriptor(self, target, publish_path: str, actual_path: str) -> typing.Dict[
		str, typing.Any]:
		actual_path = self._normalize_subscription_path(actual_path)
		return {
			"key": (target, publish_path, actual_path),
			"kind": "item" if self._is_item_subscription(publish_path) else "dir",
			"publish_path": publish_path,
			"actual_path": actual_path,
			"zk_path": self._zk_node_path(actual_path),
		}

	def _attach_watch_subscription(self, descriptor: typing.Dict[str, typing.Any]) -> None:
		subscriptions = self.WatchSubscriptions.setdefault(descriptor["zk_path"], [])
		if any(existing["key"] == descriptor["key"] for existing in subscriptions):
			return
		subscriptions.append(descriptor)

	async def _ensure_subscription_watch(self, zk_path: str) -> None:
		if zk_path in self.PersistentWatches:
			return

		mode = self._persistent_recursive_watch_mode()

		def on_watch_event(event, watch_path=zk_path):
			if event is None or getattr(event, "path", None) is None:
				return
			self.App.TaskService.schedule_threadsafe(
				self._handle_watch_event(watch_path, event)
			)

		def install_watch():
			return self.Zookeeper.Client.add_watch(zk_path, on_watch_event, mode)

		try:
			await self.Zookeeper.ProactorService.execute(install_watch)
		except kazoo.exceptions.NoNodeError:
			return

		self.PersistentWatches.add(zk_path)

	async def _remove_subscription_watch(self, zk_path: str) -> None:
		if zk_path not in self.PersistentWatches:
			return

		self.PersistentWatches.discard(zk_path)
		watcher_type_any = self._watcher_type_any()
		remove_all_watches = getattr(self.Zookeeper.Client, "remove_all_watches", None)
		if watcher_type_any is None or remove_all_watches is None:
			return

		def remove_watch():
			try:
				remove_all_watches(zk_path, watcher_type_any)
			except (kazoo.exceptions.NoNodeError, kazoo.exceptions.NoWatcherError):
				return

		try:
			await self.Zookeeper.ProactorService.execute(remove_watch)
		except kazoo.exceptions.ConnectionClosedError:
			return

	async def _remove_subscription_watches(self) -> None:
		for zk_path in list(self.PersistentWatches):
			await self._remove_subscription_watch(zk_path)

	async def _restore_subscription_watches(self) -> None:
		self._persistent_recursive_watch_mode()
		for zk_path in list(self.WatchSubscriptions.keys()):
			await self._ensure_subscription_watch(zk_path)

	def _subscription_matches_event(self, descriptor: typing.Dict[str, typing.Any], event_path: str) -> bool:
		subscription_path = descriptor["zk_path"]
		if descriptor["kind"] == "item":
			return event_path == subscription_path
		if subscription_path == '/':
			return event_path.startswith('/')
		return event_path == subscription_path or event_path.startswith(subscription_path + "/")

	async def _handle_watch_event(self, zk_path: str, event) -> None:
		event_path = getattr(event, "path", None)
		if event_path is None:
			return

		event_path = self._normalize_subscription_path(event_path)
		to_publish = set()
		for descriptor in list(self.WatchSubscriptions.get(zk_path, ())):
			if self._subscription_matches_event(descriptor, event_path):
				to_publish.add(descriptor["publish_path"])

		if len(to_publish) == 0:
			return

		self.AggrEvents.update(to_publish)
		self.AggrTimer.restart(0.2)

	async def _on_aggr_timer(self) -> None:
		to_publish = set(self.AggrEvents)
		self.AggrEvents.clear()

		for publish_path in to_publish:
			self.App.PubSub.publish("Library.change!", self, publish_path)

	async def _on_library_changed(self, event_name=None):
		if self.Zookeeper is None or not self.IsReady:
			return
		subscription_actual_paths = getattr(self, "SubscriptionActualPaths", {})

		for (target, path) in list(self.Subscriptions):

			async def do_check_path(actual_path):
				try:
					newdigest = await self._get_directory_hash(actual_path)
				except kazoo.exceptions.NoNodeError:
					newdigest = None
				if newdigest != self.NodeDigests.get(actual_path):
					self.NodeDigests[actual_path] = newdigest
					self.App.PubSub.publish("Library.change!", self, path)

			if target in {None, "global"}:
				try:
					await do_check_path(actual_path=path)
				except kazoo.exceptions.ConnectionClosedError:
					return
				except Exception:
					L.exception(
						"Failed to detect library changes on global ZooKeeper path.",
						struct_data={"path": path},
					)

			elif target == "tenant":
				try:
					tenants = await self._get_tenants()
				except kazoo.exceptions.ConnectionClosedError:
					return
				for tenant in tenants:
					try:
						await do_check_path(actual_path="/.tenants/{}{}".format(tenant, path))
					except kazoo.exceptions.ConnectionClosedError:
						return
					except Exception:
						L.exception(
							"Failed to detect library changes on tenant ZooKeeper path.",
							struct_data={"path": path, "tenant": tenant},
						)

			elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
				tenant = target[1]
				try:
					await do_check_path(actual_path="/.tenants/{}{}".format(tenant, path))
				except kazoo.exceptions.ConnectionClosedError:
					return
				except Exception:
					L.exception(
						"Failed to detect library changes on tenant-specific ZooKeeper path.",
						struct_data={"path": path, "tenant": tenant},
					)

			elif target == "personal" or (isinstance(target, tuple) and len(target) == 2 and target[0] == "personal"):
				actual_paths = subscription_actual_paths.get((target, path))
				if actual_paths is None:
					actual_path = self._subscription_personal_path(path, target)
					actual_paths = [actual_path] if actual_path is not None else []
				for actual_path in actual_paths:
					try:
						await do_check_path(actual_path=actual_path)
					except kazoo.exceptions.ConnectionClosedError:
						return
					except Exception:
						L.exception(
							"Failed to detect library changes on personal ZooKeeper path.",
							struct_data={"path": path},
						)
			else:
				raise ValueError("Unexpected target: {!r}".format((target, path)))

	async def _get_personals(self) -> typing.List[str]:
		"""
		List CredentialsIds that have custom content (i.e., directories) under /.personal.
		"""
		try:
			cred_ids = [
				c for c in await self.Zookeeper.get_children("{}/.personal".format(self.BasePath)) or []
				if not c.startswith(".")
			]
		except kazoo.exceptions.NoNodeError:
			cred_ids = []
		return cred_ids


	async def _get_tenants(self) -> typing.List[str]:
		"""
		List tenants that have custom content in the library (in the /.tenants directory).
		"""
		try:
			tenants = [
				t for t in await self.Zookeeper.get_children("{}/.tenants".format(self.BasePath)) or []
				if not t.startswith(".")
			]
		except kazoo.exceptions.NoNodeError:
			tenants = []
		return tenants


	async def find(self, filename: str) -> list:
		"""
		Recursively search for files ending with a specific name in ZooKeeper nodes, starting from the base path.

		:param filename: The filename to search for (e.g., '.setup.yaml')
		:return: A list of LibraryItem objects for files ending with the specified name,
				or an empty list if no matching files were found.
		"""
		results = []
		await self._recursive_find(self.BasePath, filename, results)
		return results

	async def _recursive_find(self, path, filename, results):
		"""
		The recursive part of the find method.

		:param path: The current path to search
		:param filename: The filename to search for
		:param results: The list where results are accumulated
		"""
		try:
			children = await self.Zookeeper.get_children(path)
			for child in children:
				full_path = "{}/{}".format(path, child).rstrip('/')
				if full_path.endswith(filename):
					item = LibraryItem(
						name=full_path[len(self.BasePath):],
						type="item",  # or "dir" if applicable
						layers=[self.Layer],
						providers=[self],
					)
					results.append(item)
				else:
					# Continue searching if it's not the file we're looking for
					if '.' not in child:  # Assuming directories don't have dots in their names
						await self._recursive_find(full_path, filename, results)
		except kazoo.exceptions.NoNodeError:
			pass  # Node does not exist, skip
		except Exception as e:
			L.warning(
				"Failed to traverse ZooKeeper path while searching the library.",
				struct_data={"path": path, "error": str(e)},
			)
