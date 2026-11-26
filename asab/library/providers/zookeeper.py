import io
import typing
import logging
import functools
import os.path
import urllib.parse

import kazoo.exceptions
import kazoo.protocol.states

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

	def __init__(self, library, path, layer, *, source):
		super().__init__(library, layer, source)

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
		if zksvc is None:
			L.critical(
				"ZooKeeper library provider requires asab.zookeeper.Module to be initialized; "
				"add asab.zookeeper.Module to Application modules.",
				struct_data={"provider_url": path},
			)
			raise SystemExit("Exit due to a critical configuration error.")

		self.ZooKeeperContainer = ZooKeeperContainer(
			zksvc,
			config_section_name=config_section_name,
			z_path=z_url
		)
		self.ZooKeeper = self.ZooKeeperContainer.ZooKeeper

		if config_section_name == 'zookeeper':
			self.FullPath += self.ZooKeeperContainer.Config['servers']
		else:
			self.FullPath += url_pieces.netloc

		# Handle `zk://` configuration
		if z_url is None and url_pieces.netloc == "" and url_pieces.path == "" and self.ZooKeeperContainer.Path != '':
			self.BasePath = '/' + self.ZooKeeperContainer.Path

		# Handle `zk://./path` configuration
		if z_url is None and url_pieces.netloc == "." and self.ZooKeeperContainer.Path != '':
			self.BasePath = '/' + self.ZooKeeperContainer.Path + self.BasePath

		self.FullPath += self.BasePath

		self.DisabledNodePath = self.build_path('/.disabled.yaml')
		self.TenantsPath = self.BasePath + "/.tenants"


		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_connected)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/SUSPENDED!", self._on_zk_lost)

		self.Subscriptions: typing.Set[typing.Tuple[typing.Union[str, tuple, None], str]] = set()
		self.SubscriptionActualPaths: typing.Dict[typing.Tuple[typing.Union[str, tuple, None], str], typing.List[str]] = {}
		self.InstalledWatchRoots: typing.Set[str] = set()


	async def finalize(self, app):
		"""
		The `finalize` function is called when the application is shutting down
		"""
		zksvc = self.App.get_service("asab.ZooKeeperService")
		await zksvc.remove(self.ZooKeeperContainer)


	async def _on_zk_connected(self, event_name, zkcontainer):
		"""
		When the ZooKeeper container is connected, set the self.ZooKeeper property to the ZooKeeper client.
		"""
		if zkcontainer != self.ZooKeeperContainer:
			return

		await self._install_disabled_watch()
		await self._remove_watches()
		await self._install_subscription_watches()
		await self._set_ready()


	async def _on_zk_lost(self, event_name, zkcontainer):
		if zkcontainer != self.ZooKeeperContainer:
			return

		await self._set_ready(ready=False)

	def _on_disabled_changed(self, event):
		"""
		Kazoo callback for `/.disabled.yaml`.
		"""
		if self.ZooKeeper is None:
			return
		self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

	async def _install_disabled_watch(self):
		"""Register a persistent watch on `/.disabled.yaml` (remove first on reconnect)."""
		if self.ZooKeeper is None:
			return

		def install():
			try:
				self.ZooKeeper.Client.remove_all_watches(
					self.DisabledNodePath,
					kazoo.protocol.states.WatcherType.ANY,
				)
			except kazoo.exceptions.ZookeeperError:
				pass
			self.ZooKeeper.Client.add_watch(
				self.DisabledNodePath,
				self._on_disabled_changed,
				kazoo.protocol.states.AddWatchMode.PERSISTENT,
			)

		await self.ZooKeeper.ProactorService.execute(install)

	def _on_tenants_discovery(self, event):
		if self.ZooKeeper is None or event.type != "CREATED" or event.path is None:
			return
		prefix = self.TenantsPath + "/"
		if not event.path.startswith(prefix):
			return
		tenant = event.path[len(prefix):]
		if "/" in tenant or not tenant or tenant.startswith("."):
			return
		self.App.TaskService.schedule(self._install_watches_for_new_tenant(tenant))

	async def _install_watches_for_new_tenant(self, tenant):
		for (target, path) in list(self.Subscriptions):
			if target != "tenant":
				continue
			actual_path = "/.tenants/{}{}".format(tenant, path)
			paths = self.SubscriptionActualPaths.setdefault((target, path), [])
			if actual_path not in paths:
				paths.append(actual_path)
			await self._install_subscription_watch(("tenant", tenant), path)

	async def _install_tenants_discovery_watch(self):
		if self.ZooKeeper is None or not any(t == "tenant" for t, _ in self.Subscriptions):
			return

		def install():
			self.ZooKeeper.Client.add_watch(
				self.TenantsPath,
				self._on_tenants_discovery,
				kazoo.protocol.states.AddWatchMode.PERSISTENT_RECURSIVE,
			)

		try:
			await self.ZooKeeper.ProactorService.execute(install)
		except (kazoo.exceptions.NoNodeError, kazoo.exceptions.ConnectionClosedError, kazoo.exceptions.ZookeeperError):
			pass

	def _on_library_changed(self, event, subscribed_path):
		"""
		Kazoo callback for persistent recursive subscription watches.
		"""
		# Kazoo invokes this callback on its connection thread, not the asyncio loop.
		# Schedule PubSub on the main loop so library change delivery stays thread-safe.
		self.App.Loop.call_soon_threadsafe(
			functools.partial(self._publish_library_change, event, subscribed_path),
		)

	def _publish_library_change(self, event, library_path):
		"""
		Emit `Library.change!` for the subscribed library directory path.
		"""
		if self.ZooKeeper is None or not self.IsReady or event.path is None:
			return

		if event.path == self.DisabledNodePath:
			return

		# TODO How to emit the event.path (the path of the changed node) and keep it line with other Library providers?
		self.App.PubSub.publish("Library.change!", self, library_path)

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

	async def read(self, path: str) -> typing.Optional[typing.IO]:
		if self.ZooKeeper is None:
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
				node_data = await self.ZooKeeper.get_data(node_path)
				if node_data is not None:
					return io.BytesIO(initial_bytes=node_data)
			return None

		except kazoo.exceptions.ConnectionClosedError:
			L.warning(
				"ZooKeeper library provider lost connection; operation rejected until reconnected.",
			)
			raise RuntimeError("Zookeeper library provider is not ready") from None

	async def list(self, path: str) -> list:
		if self.ZooKeeper is None:
			L.warning(
				"ZooKeeper library provider is not connected yet; list operation rejected.",
				struct_data={"path": path},
			)
			raise RuntimeError("Zookeeper Client has not been established (yet). Not ready.")

		# global
		global_node_path = self.build_path(path, tenant_specific=False)
		global_nodes = await self.ZooKeeper.get_children(global_node_path) or []
		global_items = await self.process_nodes(global_nodes, path, target="global")

		# tenant
		tenant_node_path = self.build_path(path, tenant_specific=True)
		if tenant_node_path != global_node_path:
			tenant_nodes = await self.ZooKeeper.get_children(tenant_node_path) or []
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
				personal_nodes = await self.ZooKeeper.get_children(personal_node_path) or []
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
					zstat = await self.ZooKeeper.exists(node_path) if node_path else None
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
		self.Subscriptions.add((target, path))

		if target in {None, "global"}:
			self.SubscriptionActualPaths[("global", path)] = [path]

		elif target == "tenant":
			actual_paths = []
			for tenant in await self._get_tenants():
				actual_paths.append("/.tenants/{}{}".format(tenant, path))
			self.SubscriptionActualPaths[(target, path)] = actual_paths

		elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			_, tenant = target
			self.SubscriptionActualPaths[(target, path)] = ["/.tenants/{}{}".format(tenant, path)]

		elif target == "personal" or (isinstance(target, tuple) and len(target) == 2 and target[0] == "personal"):
			actual_path = self._subscription_personal_path(path, target)
			if actual_path is not None:
				self.SubscriptionActualPaths[(target, path)] = [actual_path]
			else:
				self.SubscriptionActualPaths[(target, path)] = []
		else:
			raise ValueError("Unexpected target: {!r}".format(target))

		if self.ZooKeeper is not None:
			await self._install_subscription_watch(target, path)
			if target == "tenant":
				await self._install_tenants_discovery_watch()

	async def _remove_watches(self):
		"""
		Remove persistent recursive watches for current subscriptions before reinstalling them after a ZooKeeper reconnect, so callbacks are not registered twice.
		"""
		if self.ZooKeeper is None:
			return

		self.InstalledWatchRoots.clear()

		if any(target == "tenant" for target, _ in self.Subscriptions):
			def remove_tenants_watches():
				try:
					self.ZooKeeper.Client.remove_all_watches(self.TenantsPath, kazoo.protocol.states.WatcherType.ANY)
				except kazoo.exceptions.ZookeeperError:
					pass

			try:
				await self.ZooKeeper.ProactorService.execute(remove_tenants_watches)
			except kazoo.exceptions.ConnectionClosedError:
				return

		processed_zk_roots = set()
		for (target, path) in list(self.Subscriptions):
			for actual_path in self.SubscriptionActualPaths.get((target, path), []):
				zk_root = (self.BasePath + actual_path).rstrip("/")
				if not zk_root:
					zk_root = "/"
				if zk_root in processed_zk_roots:
					continue
				processed_zk_roots.add(zk_root)

				def remove(zk_root=zk_root):
					try:
						self.ZooKeeper.Client.remove_all_watches(
							zk_root,
							kazoo.protocol.states.WatcherType.ANY,
						)
					except kazoo.exceptions.ZookeeperError:
						# No watch on this path or node missing — safe to continue.
						pass

				try:
					await self.ZooKeeper.ProactorService.execute(remove)
				except kazoo.exceptions.ConnectionClosedError:
					return

	async def _install_subscription_watch(self, target, path):
		"""
		Register persistent recursive watch for a library subscription.
		"""
		if self.ZooKeeper is None:
			return

		async def do_install_watch(actual_path, subscribed_path=path):
			zk_root = (self.BasePath + actual_path).rstrip("/")
			if not zk_root:
				zk_root = "/"

			if zk_root in self.InstalledWatchRoots:
				return

			def install():
				# Kazoo invokes the watch callback with only `event`. This callable is stored
				# on the client and binds `subscribed_path` to the ZK watch at install time.
				def on_watch(event, subscribed_path=subscribed_path):
					self._on_library_changed(event, subscribed_path)

				self.ZooKeeper.Client.add_watch(
					zk_root,
					on_watch,
					kazoo.protocol.states.AddWatchMode.PERSISTENT_RECURSIVE,
				)

			await self.ZooKeeper.ProactorService.execute(install)
			self.InstalledWatchRoots.add(zk_root)

		if target in {None, "global"}:
			try:
				await do_install_watch(actual_path=path)
			except kazoo.exceptions.ConnectionClosedError:
				return
			except Exception:
				L.exception(
					"Failed to install library watch on global ZooKeeper path.",
					struct_data={"path": path},
				)

		elif target == "tenant":
			try:
				tenants = await self._get_tenants()
				self.SubscriptionActualPaths[(target, path)] = [
					"/.tenants/{}{}".format(tenant, path) for tenant in tenants
				]
			except kazoo.exceptions.ConnectionClosedError:
				return
			for tenant in tenants:
				try:
					await do_install_watch(actual_path="/.tenants/{}{}".format(tenant, path))
				except kazoo.exceptions.ConnectionClosedError:
					return
				except Exception:
					L.exception(
						"Failed to install library watch on tenant ZooKeeper path.",
						struct_data={"path": path, "tenant": tenant},
					)

		elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			tenant = target[1]
			try:
				await do_install_watch(actual_path="/.tenants/{}{}".format(tenant, path))
			except kazoo.exceptions.ConnectionClosedError:
				return
			except Exception:
				L.exception(
					"Failed to install library watch on tenant-specific ZooKeeper path.",
					struct_data={"path": path, "tenant": tenant},
				)

		elif target == "personal" or (isinstance(target, tuple) and len(target) == 2 and target[0] == "personal"):
			actual_paths = self.SubscriptionActualPaths.get((target, path))
			if actual_paths is None:
				actual_path = self._subscription_personal_path(path, target)
				actual_paths = [actual_path] if actual_path is not None else []
			for actual_path in actual_paths:
				try:
					await do_install_watch(actual_path=actual_path)
				except kazoo.exceptions.ConnectionClosedError:
					return
				except Exception:
					L.exception(
						"Failed to install library watch on personal ZooKeeper path.",
						struct_data={"path": path},
					)
		else:
			raise ValueError("Unexpected target: {!r}".format((target, path)))

	async def _install_subscription_watches(self):
		"""
		Register PERSISTENT_RECURSIVE watches for every current subscription.
		"""
		if self.ZooKeeper is None:
			return

		for (target, path) in list(self.Subscriptions):
			await self._install_subscription_watch(target, path)
		await self._install_tenants_discovery_watch()

	async def _get_personals(self) -> typing.List[str]:
		"""
		List CredentialsIds that have custom content (i.e., directories) under /.personal.
		"""
		try:
			cred_ids = [
				c for c in await self.ZooKeeper.get_children("{}/.personal".format(self.BasePath)) or []
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
				t for t in await self.ZooKeeper.get_children("{}/.tenants".format(self.BasePath)) or []
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
			children = await self.ZooKeeper.get_children(path)
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
