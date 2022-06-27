import logging
import os.path
import urllib.parse
import asab.zookeeper

from .abc import LibraryProviderABC

#

L = logging.getLogger(__name__)


#


class ZooKeeperLibraryProvider(LibraryProviderABC):

	def __init__(self, app, path):
		super().__init__(app, path)
		self.App = app
		self.Path = path
		url_pieces = urllib.parse.urlparse(self.Path)
		self.BasePath = url_pieces.path
		# remove leading and trailing slashes.
		if self.BasePath.startswith("/"):
			self.BasePath = self.BasePath.lstrip("/")
		if self.BasePath.endswith("/"):
			self.BasePath = self.BasePath.rstrip("/")
		zksvc = self.App.get_service("asab.ZooKeeperService")
		# Initialize ZooKeeper client
		self.ZookeeperContainer = asab.zookeeper.ZooKeeperContainer(
			zksvc,
			config_section_name='',
			z_path=self.Path
		)
		self.Zookeeper = None
		self.DisabledPaths = None
		self.App.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper

	async def _on_zk_ready(self, event_name, zkcontainer):
		if zkcontainer == self.ZookeeperContainer:
			self.DisabledPaths = await self.read(".disabled.yaml")

	async def finalize(self, app):
		# close client
		await self.Zookeeper._stop()

	async def read(self, path):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return
		node_path = "{}/{}".format(self.BasePath, path)
		node_data = await self.Zookeeper.get_data(node_path)

		return node_data

	async def list(self, path, tenant, recursive=True):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			return
		node_names = list()
		node_path = self.get_zookeeper_path(path2=path)
		await self._list_by_node_path(node_path, node_names, tenant, recursive=recursive)
		return node_names

	async def _list_by_node_path(self, node_path, node_names, tenant, recursive=True):
		"""
		Recursive function to list all nested nodes within the ZooKeeper library.
		"""
		nodes = await self.Zookeeper.get_children(node_path)
		if nodes is None:
			L.warning("Path {} does not exist in ZK".format(node_path))
			return None
		for node in nodes:
			try:
				nested_node_path = self.get_zookeeper_path(path1=node_path, path2=node)
				if recursive:
					await self._list_by_node_path(nested_node_path, node_names, recursive)
					if self.is_path_disabled(nested_node_path, tenant) is True:
						node_names.append(nested_node_path)
					else:
						continue
			except Exception as e:
				L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))

	def is_path_disabled(self, path, tenant):
		get_disabled_tenant_list = self.DisabledPaths.get(path, [])
		if path in self.DisabledPaths:
			if tenant in get_disabled_tenant_list or '*' in get_disabled_tenant_list:
				return True
			else:
				return False

	def get_zookeeper_path(self, path2, path1=None):
		# if path1 is not provided we assume path1 is self.Library
		if path1 is None:
			path = os.path.join(self.BasePath, path2)
		else:
			path = os.path.join(path1, path2)
		# remove redundant separators
		zookeeper_path = os.path.normpath(path)
		# get rid of first slash
		return zookeeper_path.lstrip("/")
