import logging
import kazoo.exceptions
import urllib.parse
import asab.zookeeper
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
		url_pieces = urllib.parse.urlparse(self.Path)
		self.BasePath = url_pieces.path
		if self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]
		zksvc = self.App.get_service("asab.ZooKeeperService")
		# for now it is just yaml
		self.FileExtentions = frozenset({'.yaml'})
		# Initialize ZooKeeper client
		self.ZookeeperContainer = asab.zookeeper.ZooKeeperContainer(
			zksvc,
			config_section_name='',
			z_path=self.Path
		)
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper
		self.App.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)
		self.DisabledPaths = None

	async def _on_zk_ready(self, event_name, zkcontainer):
		if zkcontainer.ZooKeeperPath == self.BasePath:
			self.DisabledPaths = await self.read(".disabled.yaml")

	async def read(self, path):
		node_path = "{}/{}".format(self.BasePath, path)

		try:
			node_data = await self.Zookeeper.get_data(node_path)
		except kazoo.exceptions.NoNodeError:
			return None

		return node_data

	async def _get_children_recursive(self, path, tenant):
		children_list = []
		children = await self.Zookeeper.get_children("{}/{}".format(self.BasePath, path))
		if children is None:
			return children

		children.sort(key=lambda name: name)

		for node_name in children:
			node_type = {}
			path_file = '/'.join([path, node_name])
			path_file = path_file.strip("/")
			if node_name.startswith("."):
				continue
			nodename, node_extension = os.path.splitext(node_name)
			if node_extension in self.FileExtentions:
				node_type["file_name"] = node_name
				node_type["type"] = "file"
				get_disabled_tenant_list = self.DisabledPaths.get(path_file, [])
				if path_file in self.DisabledPaths:
					if tenant in get_disabled_tenant_list or '*' in get_disabled_tenant_list:
						is_disabled = True
					else:
						is_disabled = False
				else:
					is_disabled = False
				node_type["is_disabled"] = is_disabled
				children_list.append(node_type)

			else:
				node_item = await self._get_children_recursive("{}/{}".format(path, node_name), tenant)
				if node_item is None:
					L.error("Error while processing the list. Use correct extension for node {}".format(node_name))
				if len(node_item) > 0:
					node_type.update({node_name: node_item})
					node_type["type"] = "directory"
					children_list.append(node_type)
		return children_list

	async def _get_children_flat(self, path, tenant):
		children_list = []
		item = await self.Zookeeper.get_children("{}/{}".format(
			self.BasePath, path)
		)

		if item is None:
			return item

		item.sort(key=lambda name: name)

		for node_name in item:
			node_type = {}
			path_file = '/'.join([self.BasePath, path, node_name])
			node_item = await self.Zookeeper.get_children(path_file)
			if len(node_item) > 0:
				node_type.update({node_name: node_item})
				node_type["type"] = "directory"
				children_list.append(node_type)
			else:
				path_file = '/'.join([path, node_name])
				node_type["file_name"] = node_name
				node_type["type"] = "file"
				# find out if the path is disabled
				get_disabled_tenant_list = self.DisabledPaths.get(path_file, [])
				if path_file in self.DisabledPaths:
					if tenant in get_disabled_tenant_list or '*' in get_disabled_tenant_list:
						is_disabled = True
					else:
						is_disabled = False
				else:
					is_disabled = False
				node_type["is_disabled"] = is_disabled
				children_list.append(node_type)

		return children_list

	async def get_children(self, path, recursive=False, tenant=None):
		# get a list with modified children as contents
		if recursive:
			library_list = await self._get_children_recursive(path, tenant)

		else:
			library_list = await self._get_children_flat(path, tenant)

		return library_list

	async def finalize(self, app):
		# close client
		await self.Zookeeper._stop()
