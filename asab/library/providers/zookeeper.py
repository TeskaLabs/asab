import logging
import kazoo.exceptions
import urllib.parse
import asab.zookeeper
import tempfile
import tarfile
import io
import time
import os

from .abc import LibraryProviderABC

#

L = logging.getLogger(__name__)

#


class ZooKeeperLibraryProvider(LibraryProviderABC):


	def __init__(self, app, path):
		super().__init__(app, path)
		self.App = app
		self.Path = path
		self.FileExtentions = frozenset({'.yaml', '.json', '.png', ',jpeg', '.xml', '.conf', '.html'})
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


	async def list(self, path):
		if self.Zookeeper is None:
			return

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
					# Remove library path from the beginning of node names
					node_names.append(
						nested_node_path.replace("{}/".format(self.BasePath), "")
					)
				except Exception as e:
					L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))

		except kazoo.exceptions.NoNodeError:
			return None


	async def export_library(self, path):
		# get a list with modified children as contents
		fileobj = tempfile.TemporaryFile()
		tarobj = tarfile.open(name=None, mode='w:gz', fileobj=fileobj)
		tarobj = await self.write_to_tar(path, tarobj)
		tarobj.close()
		fileobj.seek(0)
		return fileobj

	async def write_to_tar(self, path, tarobj):
		children = await self.Zookeeper.get_children("{}/{}".format(self.BasePath, path))
		if children is None:
			pass

		children.sort(key=lambda name: name)
		for node_name in children:
			if node_name.startswith("."):
				continue

			_, node_extension = os.path.splitext(node_name)
			if node_extension in self.FileExtentions:
				self.BasePath = self.BasePath.lstrip("/")
				path = path.lstrip("/")
				if len(path) == 0:
					path_data = '/'.join([self.BasePath, node_name])
				else:
					path_data = '/'.join([self.BasePath, path, node_name])
				my_data = await self.Zookeeper.get_data(path_data)
				f = io.BytesIO(my_data)
				info = tarfile.TarInfo(path_data)
				info.size = len(my_data)
				info.mtime = time.time()
				tarobj.addfile(tarinfo=info, fileobj=f)

			else:
				await self.write_to_tar("{}/{}".format(path, node_name), tarobj)
		return tarobj
