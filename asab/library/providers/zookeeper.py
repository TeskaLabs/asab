import logging
import kazoo.exceptions
import urllib.parse
import asab.zookeeper

from .abc import LibraryProviderABC

#

L = logging.getLogger(__name__)

#


class ZooKeeperLibraryProvider(LibraryProviderABC):


	def __init__(self, app, path, encoding="utf-8"):
		super().__init__(app, path)
		self.App = app
		self.Encoding = encoding
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
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper

	async def initialize(self, app):
		pass


	async def read(self, path):
		node_path = "{}/{}".format(self.BasePath, path)

		try:
			node_data = await self.Zookeeper.get_data(node_path)
		except kazoo.exceptions.NoNodeError:
			return None

		return node_data.decode(self.Encoding)


	async def list(self, path):
		recursive = path.endswith("*")

		if recursive:
			path = path[:-2]

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
					# List only YAML files
					if not nested_node_path.endswith(".yaml"):
						continue
					# Remove library path from the beginning of node names
					node_names.append(
						nested_node_path.replace("{}/".format(self.BasePath), "")
					)
				except Exception as e:
					L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))

		except kazoo.exceptions.NoNodeError:
			return None

	async def finalize(self, app):
		# close client
		await self.Zookeeper._stop()
