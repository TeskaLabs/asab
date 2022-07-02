import logging
import os.path
import urllib.parse

import yaml

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
		self.BasePath = url_pieces.path.lstrip("/")
		# remove leading.
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
		self.DisabledPaths = None
		self.FileExtentions = {'.yaml'}
		self.App.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)
		self.Zookeeper = self.ZookeeperContainer.ZooKeeper


	async def finalize(self, app):
		"""
		The `finalize` function is called when the application is shutting down
		"""
		# close client
		await self.Zookeeper._stop()


	async def _on_zk_ready(self, event_name, zkcontainer):
		"""
		When the Zookeeper container is ready, set the self.Zookeeper property to the Zookeeper object.
		"""
		if zkcontainer == self.ZookeeperContainer:
			self.Zookeeper = self.ZookeeperContainer.ZooKeeper


	async def read(self, path):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot read {}".format(path))
			return
		node_path = "{}/{}".format(self.BasePath, path)
		node_data = await self.Zookeeper.get_data(node_path)

		return node_data.decode('utf-8')


	async def list(self, path, tenant, recursive):
		if self.Zookeeper is None:
			L.warning("Zookeeper Client has not been established (yet). Cannot list {}".format(path))
			return
		node_names = list()
		node_path = self.create_zookeeper_path(path1=path)
		await self._list_by_node_path(node_path, node_names, tenant, recursive)
		return node_names


	async def _list_by_node_path(self, node_path, node_names, tenant, recursive):
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
					await self._list_by_node_path(nested_node_path, node_names, tenant, recursive)
				nodename, node_extension = os.path.splitext(node)

				# do not add nodes that starts-with '.' or they are not part of file-extent.ion to our list
				if nodename.startswith(".") or node_extension not in self.FileExtentions:
					continue

				nested_node_path = nested_node_path.replace("{}/".format(self.BasePath), "")
				# if tenant is None just add the path to the list.
				if tenant is None:
					node_names.append(nested_node_path)

				else:
					# add only disabled yaml file names to list and return.
					if self.is_path_disabled(nested_node_path, tenant) is True:
						node_names.append(nested_node_path)
			except Exception as e:
				L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))


	async def _load_disabled(self):
		try:
			disabled_data = await self.read(".disabled.yaml")
			return yaml.safe_load(disabled_data)
		except Exception as e:
			L.error("The following exception occurred while loading disabled list: '{}'.".format(e))
			return None


	def is_path_disabled(self, path, tenant):
		"""
			This method checks if the path is disabled for a specific tenant.
			Returns True if yes or it returns False.
		"""
		get_disabled_tenant_list = self.DisabledPaths.get(path, [])
		# return True if the current path is present  is the list of disabled paths.
		if path in self.DisabledPaths:
			if tenant in get_disabled_tenant_list or '*' in get_disabled_tenant_list:
				return True
			else:
				return False

	def create_zookeeper_path(self, path1, path2=None):
		"""
			This method created path that can be used by zookeeper for CRUD operations.
			-if path2 is not passed provided we assume path1 is self.Library.
			-path1 is always absolute.
		"""
		if path2 is None:
			path = os.path.join(path1, self.BasePath)
		else:
			path = os.path.join(path1, path2)
		# remove redundant separators
		zookeeper_path = os.path.normpath(path)
		# get rid of first slash
		return zookeeper_path.lstrip("/")
