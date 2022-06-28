import logging
import os.path
import urllib.parse
import asab.zookeeper
import yaml

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
		self.BasePath = url_pieces.path.lstrip("/")
		# remove leading.
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
			self.DisabledPaths = await self._load_disabled()

	async def _load_disabled(self):
		try:
			disabled_data = await self.read(".disabled.yaml")
			return yaml.safe_load(disabled_data)
		except Exception as e:
			L.error("The following exception occurred while loading disabled list: '{}'.".format(e))
			return None

	async def finalize(self, app):
		# close client
		await self.Zookeeper._stop()

	async def read(self, path):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return
		node_path = "{}/{}".format(self.BasePath, path)
		node_data = await self.Zookeeper.get_data(node_path)

		return node_data.decode('utf-8')

	async def list(self, path, tenant, recursive=True):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			return
		node_names = list()
		node_path = self.create_zookeeper_path(path1=path)
		return await self._list_by_node_path(node_path, node_names, tenant, recursive=recursive)

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
				nested_node_path = self.create_zookeeper_path(path1=node_path, path2=node)
				if recursive:
					await self._list_by_node_path(nested_node_path, node_names, recursive)
					# add only disabled yaml file names to list and return.
					nested_node_path = nested_node_path.replace("{}/".format(self.BasePath), "")
					if self.is_path_disabled(nested_node_path, tenant) is True:
						node_names.append(nested_node_path)
						nodes = node_names
					else:
						continue
					return nodes
			except Exception as e:
				L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))

	def is_path_disabled(self, path, tenant):
		# obtain every path is DisabledPaths
		get_disabled_tenant_list = self.DisabledPaths.get(path, [])
		# return True if it is present
		if path in self.DisabledPaths:
			if tenant in get_disabled_tenant_list or '*' in get_disabled_tenant_list:
				return True
			else:
				return False

	def create_zookeeper_path(self, path1, path2=None):
		# if path1 is not provided we assume path1 is self.Library
		if path2 is None:
			path = os.path.join(path1, self.BasePath)
		else:
			path = os.path.join(path1, path2)
		# remove redundant separators
		zookeeper_path = os.path.normpath(path)
		# get rid of first slash
		return zookeeper_path.lstrip("/")
