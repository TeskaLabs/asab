import logging
import kazoo.exceptions
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
		if self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]
		zksvc = self.App.get_service("asab.ZooKeeperService")
		# Initialize ZooKeeper client
		self.ZookeeperContainer = asab.zookeeper.ZooKeeperContainer(
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
			return

		node_path = "{}/{}".format(self.BasePath, path)

		try:
			node_data = await self.Zookeeper.get_data(node_path)
		except kazoo.exceptions.NoNodeError:
			return None

		return node_data


	async def list(self, path, recursive=True):
		if self.Zookeeper is None:
			return

		node_names = list()
		node_path = "{}/{}".format(self.BasePath, path)
		await self._list_by_node_path(node_path, node_names, recursive=recursive)
		return node_names


	async def _list_by_node_path(self, node_path, node_names, recursive=True):
		"""
		Recursive function to list all nested nodes within the ZooKeeper library.
		"""
		try:
			for node in await self.Zookeeper.get_children(node_path):
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

		except kazoo.exceptions.NoNodeError:
			return None
