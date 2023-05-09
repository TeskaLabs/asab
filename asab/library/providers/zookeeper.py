import io
import typing
import logging
import functools
import os.path
import urllib.parse

import kazoo.exceptions

from .abc import LibraryProviderABC
from ..item import LibraryItem
from ...zookeeper import ZooKeeperContainer

#

L = logging.getLogger(__name__)

#


class ZooKeeperLibraryProvider(LibraryProviderABC):

	"""

	Configuration variant:


	1) ZooKeeper provider is fully configured from [zookeeper] section

	```
	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/library

	[library]
	providers:
		zk://
	```


	2) ZooKeeper provider is configured by `servers` from [zookeeper] section and path from URL

	Path will be `/library'.

	```
	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk:///library
	```


	2.1) ZooKeeper provider is configured by `servers` from [zookeeper] section and path from URL

	Path will be `/', this is a special case to 2)

	```
	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk:///
	```

	3) ZooKeeper provider is fully configured from URL

	```
	[library]
	providers:
		zk://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/library
	```

	4) ZooKeeper provider is configured by `servers` from [zookeeper] section and  joined `path` from [zookeeper] and
	path from URL

	Path will be `/else/library'

	```
	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk://./library
	```

	If `path` from [zookeeper] section is missing, an application class name will be used
	Ex. `/BSQueryApp/library'

	"""

	def __init__(self, library, path):
		super().__init__(library)

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

		L.info("Version changed", struct_data={'version': version, 'name': self.Library.Name})
		self.App.PubSub.publish("Library.change!", self, "TODO")


	async def read(self, path: str) -> typing.IO:
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return None

		node_path = self.build_path(path)

		try:
			node_data = await self.Zookeeper.get_data(node_path)
		except kazoo.exceptions.NoNodeError:
			return None

		# Consider adding other exceptions from Kazoo to indicate common non-critical errors

		if node_data is not None:
			return io.BytesIO(initial_bytes=node_data)
		else:
			return None


	async def list(self, path: str) -> list:
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			raise RuntimeError("Not ready")

		node_path = self.build_path(path)

		nodes = await self.Zookeeper.get_children(node_path)
		if nodes is None:
			raise KeyError("Not '{}' found".format(node_path))

		items = []
		for node in nodes:

			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), node.split(os.path.sep), False)
			if startswithdot:
				continue

			if '.' in node:  # We detect files in zookeeper by presence of the dot in the filename,
				fname = path + node
				ftype = "item"
			else:
				fname = path + node + '/'
				ftype = "dir"

			items.append(LibraryItem(
				name=fname,
				type=ftype,
				providers=[self],
			))

		return items


	def build_path(self, path):
		"""
		It takes a path in the library and transforms in into a path within Zookeeper.
		It does also series of sanity checks (asserts).

		IMPORTANT: If you encounter asserting failure, don't remove assert.
		It means that your code is incorrect.
		"""
		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		# Zookeeper path should not have forward slash at the end of path
		node_path = node_path.rstrip("/")

		assert '//' not in node_path
		assert node_path[0] == '/'

		return node_path
