import logging
import urllib.parse

from .abc import LibraryProviderABC
from ..zookeeper import ZooKeeperContainer

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
		if self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]

		# Initialize ZooKeeper client
		zksvc = self.App.get_service("asab.ZooKeeperService")
		self.ZookeeperContainer = ZooKeeperContainer(
			zksvc,
			config_section_name='',
			z_path=self.Path
		)

		self.Zookeeper = None
		self.App.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)


	async def finalize(self, app):
		# close client
		await self.Zookeeper._stop()


	async def _on_zk_ready(self, event_name, zkcontainer):
		if zkcontainer == self.ZookeeperContainer:
			self.Zookeeper = self.ZookeeperContainer.ZooKeeper


	async def read(self, path):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return

		node_path = "{}/{}".format(self.BasePath, path)
		node_data = await self.Zookeeper.get_data(node_path)

		return node_data


	async def list(self, path, recursive=True):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			return

		node_names = list()
		node_path = "{}/{}".format(self.BasePath, path)
		await self._list_by_node_path(node_path, node_names, recursive=recursive)

		return node_names


	async def _list_by_node_path(self, node_path, node_names, recursive=True):
		"""
		Recursive function to list all nested nodes within the ZooKeeper library.
		"""
		nodes = await self.Zookeeper.get_children(node_path)
		if nodes is None:
			L.warning("Path {} does not exist in ZK".format(node_path))
			return None

		for node in nodes:
			try:
				nested_node_path = "{}/{}".format(node_path, node)
				if recursive:
					await self._list_by_node_path(nested_node_path, node_names, recursive)
				# Remove library path from the beginning of node names
				node_names.append(
					nested_node_path.replace("{}/".format(self.BasePath), "")
				)

			except Exception as e:
				L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))
