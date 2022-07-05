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

	def __init__(self, library, path):
		super().__init__(library)

		url_pieces = urllib.parse.urlparse(path)

		self.BasePath = url_pieces.path.lstrip("/")
		while self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]
		self.BasePath = '/' + self.BasePath

		if url_pieces.netloc == "":
			# if netloc is not providede `zk:///path`, then use `zookeeper` section from config
			config_section_name = 'zookeeper'
			z_url = None
		else:
			config_section_name = ''
			z_url = url_pieces  # TODO: Not correct

		# Initialize ZooKeeper client
		zksvc = self.App.get_service("asab.ZooKeeperService")
		self.ZookeeperContainer = ZooKeeperContainer(
			zksvc,
			config_section_name=config_section_name,
			z_path=z_url
		)
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper

		self.App.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)


	async def finalize(self, app):
		"""
		The `finalize` function is called when the application is shutting down
		"""
		await self.Zookeeper._stop()


	async def _on_zk_ready(self, event_name, zkcontainer):
		"""
		When the Zookeeper container is ready, set the self.Zookeeper property to the Zookeeper object.
		"""
		if zkcontainer == self.ZookeeperContainer:
			self.Zookeeper = self.ZookeeperContainer.ZooKeeper
			self._set_ready()


	async def read(self, path):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return None

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		try:
			node_data = await self.Zookeeper.get_data(node_path)
		except kazoo.exceptions.NoNodeError:
			return None
		# Consider adding other exceptions from Kazoo to indicate common non-critical errors

		return node_data


	async def list(self, path: str) -> list:
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			return None

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		nodes = await self.Zookeeper.get_children(node_path)
		if nodes is None:
			raise KeyError("Not '{}' found".format(node_path))

		items = []
		for node in nodes:

			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), node.split(os.path.sep), False)
			if startswithdot:
				continue

			items.append(LibraryItem(
				name=(path + node) if path == '/' else (path + '/' + node),
				type="item" if '.' in node else "dir",  # We detect files in zookeeper by presence of the dot in the filename,
				providers=[self],
			))

		return items
