import io
import hashlib
import typing
import logging
import functools
import os.path
import urllib.parse

import kazoo.exceptions

from .abc import LibraryProviderABC
from ..item import LibraryItem
from ...zookeeper import ZooKeeperContainer
from ...contextvars import Tenant

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

		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_connected)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/LOST!", self._on_zk_lost)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/SUSPENDED!", self._on_zk_lost)
		self.App.PubSub.subscribe("Application.tick/60!", self._get_version_counter)

		# This is a contingency check for changes for subscribed folders in library even without version counter change.
		self.App.PubSub.subscribe("Application.tick/600!", self._on_library_changed)

		self.Subscriptions: typing.Iterable[str] = set()
		self.NodeDigests: typing.Dict[str, bytes] = {}


	async def finalize(self, app):
		"""
		The `finalize` function is called when the application is shutting down
		"""
		await self.Zookeeper._stop()


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

		await self._set_ready()


	async def _on_zk_lost(self, event_name, zkcontainer):
		if zkcontainer != self.ZookeeperContainer:
			return

		await self._set_ready(ready=False)


	async def _get_version_counter(self, event_name=None):
		if self.Zookeeper is None:
			return

		version = await self.Zookeeper.get_data(self.VersionNodePath)
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

	async def read(self, path: str) -> typing.IO:
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			raise RuntimeError("Zookeeper Client has not been established (yet). Not ready.")

		try:
			# Try tenant-specific path first
			node_path = self.build_path(path, tenant_specific=True)
			node_data = await self.Zookeeper.get_data(node_path)

			# If not found, try the normal path
			if node_data is None:
				node_path = self.build_path(path, tenant_specific=False)
				node_data = await self.Zookeeper.get_data(node_path)

			if node_data is not None:
				return io.BytesIO(initial_bytes=node_data)
			else:
				return None

		except kazoo.exceptions.ConnectionClosedError:
			L.warning("Zookeeper library provider is not ready")
			raise RuntimeError("Zookeeper library provider is not ready")

	async def list(self, path: str) -> list:
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			raise RuntimeError("Zookeeper Client has not been established (yet). Not ready.")

		# Process global nodes
		global_node_path = self.build_path(path, tenant_specific=False)
		global_nodes = await self.Zookeeper.get_children(global_node_path) or []
		global_items = await self.process_nodes(global_nodes, path)

		# Process tenant-specific nodes
		tenant_node_path = self.build_path(path, tenant_specific=True)
		if tenant_node_path != global_node_path:
			tenant_nodes = await self.Zookeeper.get_children(tenant_node_path) or []
			tenant_items = await self.process_nodes(tenant_nodes, path, target="tenant")
		else:
			tenant_items = []
		# Combine items, with tenant items taking precedence over global ones
		combined_items = {item.name: item for item in global_items}
		combined_items.update({item.name: item for item in tenant_items})

		return list(combined_items.values())

	async def process_nodes(self, nodes, base_path, target="global"):
		"""
		Processes a list of nodes and creates corresponding LibraryItem objects with their size.

		Args:
			nodes (list): List of node names to process.
			base_path (str): The base path for the nodes.
			target (str): Specifies the target context, e.g., "tenant" or "global".

		Returns:
			list: A list of LibraryItem objects with size information.
		"""
		items = []
		for node in nodes:
			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), node.split(os.path.sep), False)
			if startswithdot:
				continue

			# Determine if this is a file or directory
			if '.' in node and not node.endswith(('.io', '.d')):  # File check
				fname = "{}/{}".format(base_path.rstrip("/"), node)
				ftype = "item"

				# Retrieve node size for items only
				try:
					node_path = self.build_path(fname, tenant_specific=(target == "tenant"))
					zstat = self.Zookeeper.Client.exists(node_path)
					size = zstat.dataLength if zstat else 0
				except kazoo.exceptions.NoNodeError:
					size = 0
				except Exception as e:
					L.warning("Failed to retrieve size for node {}: {}".format(node_path, e))
					size = 0
			else:  # Directory check
				fname = "{}/{}".format(base_path.rstrip("/"), node)
				ftype = "dir"
				size = 0  # Directories do not have a size

			# Add the item with the specified target and size
			items.append(LibraryItem(
				name=fname,
				type=ftype,
				layer=self.Layer,
				providers=[self],
				target=target,
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

		if target is None:
			# Back-compat (pubsub callback must be called without `target` argument)
			# Watch path globally
			self.NodeDigests[path] = await self._get_directory_hash(path)
		elif target == "global":
			# Watch path globally
			self.NodeDigests[path] = await self._get_directory_hash(path)
		elif target == "tenant":
			# Watch path in all tenants
			for tenant in await self._get_tenants():
				actual_path = "/.tenants/{}{}".format(tenant, path)
				self.NodeDigests[actual_path] = await self._get_directory_hash(actual_path)
		elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			# Watch path in a specific tenant
			_, tenant = target
			actual_path = "/.tenants/{}{}".format(tenant, path)
			self.NodeDigests[actual_path] = await self._get_directory_hash(actual_path)
		else:
			raise ValueError("Unexpected target: {!r}".format(target))


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


	async def _on_library_changed(self, event_name=None):
		"""
		Check watched paths and publish a pubsub message for every one that has changed.
		"""

		for (target, path) in self.Subscriptions:

			async def do_check_path(actual_path):
				try:
					newdigest = await self._get_directory_hash(actual_path)
				except kazoo.exceptions.NoNodeError:
					# This node is either deleted or has never existed.
					newdigest = None

				if newdigest != self.NodeDigests.get(actual_path):
					self.NodeDigests[actual_path] = newdigest
					self.App.PubSub.publish("Library.change!", self, path)

			if target in {None, "global"}:
				try:
					await do_check_path(actual_path=path)
				except Exception as e:
					L.error(
						"Failed to process library changes: '{}'".format(e),
						struct_data={"path": path},
					)

			elif target == "tenant":
				for tenant in await self._get_tenants():
					try:
						await do_check_path(actual_path="/.tenants/{}{}".format(tenant, path))
					except Exception as e:
						L.error(
							"Failed to process library changes: '{}'".format(e),
							struct_data={"path": path, "tenant": tenant},
						)

			elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
				tenant = target[1]
				try:
					await do_check_path(actual_path="/.tenants/{}{}".format(tenant, path))
				except Exception as e:
					L.error(
						"Failed to process library changes: '{}'".format(e),
						struct_data={"path": path, "tenant": tenant},
					)
			else:
				raise ValueError("Unexpected target: {!r}".format((target, path)))


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
						layer=self.Layer,
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
			L.warning("Error accessing {}: {}".format(path, e))
