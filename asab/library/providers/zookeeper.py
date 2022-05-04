import logging
import asyncio

import aiozk
import aiozk.transaction
import kazoo.exceptions

import asab.zookeeper.container

from aiozk.recipes.base_watcher import BaseWatcher

from .abc import LibraryProviderABC

#

L = logging.getLogger(__name__)

#


class ZooKeeperLibraryProvider(LibraryProviderABC):


	def __init__(self, app, splang_instance, path, encoding="utf-8"):
		super().__init__(app, splang_instance, path)

		# Obtain encoding
		self.Encoding = encoding

		# Get url and path
		path_split = path.replace("zk://", "").split("/", 1)
		self.ZooKeeperUrl = path_split[0]
		self.LibraryBasePath = path_split[1]

		# Initialize ZooKeeper client
		self.ZooKeeperClient = aiozk.ZKClient(
			self.ZooKeeperUrl,
			session_timeout=900,
			read_timeout=900,
		)

		# # Prepare watcher to observe for changes in the library
		# self.ZooKeeperWatcher = ModifyWatcher(base_path=self.LibraryBasePath)

		app.PubSub.subscribe("Application.exit!", self._on_exit)


	async def initialize(self):
		# Start the client
		await self.ZooKeeperClient.start()
		await self.ZooKeeperClient.ensure_path(self.LibraryBasePath)

		# # Initialize watcher for ZooKeeper
		# self.ZooKeeperWatcher.set_client(self.ZooKeeperClient)
		# self.ZooKeeperWatcher.add_callback(self.LibraryBasePath, self._library_change_callback)


	# async def _library_change_callback(self, result):
	# 	self.App.PubSub.publish("SPLangLibrary.changed!", {"path": self.LibraryBasePath})
	# 	self.ZooKeeperWatcher.remove_callback(self.LibraryBasePath, self._library_change_callback)
	#
	# 	# Repeat the watch
	# 	self.ZooKeeperWatcher.add_callback(self.LibraryBasePath, self._library_change_callback)
	#
	#
	# async def _on_exit(self, message_type):
	# 	self.ZooKeeperWatcher.remove_callback(self.LibraryBasePath, self._library_change_callback)


	async def read(self, path):
		node_path = "{}/{}".format(self.LibraryBasePath, path)

		try:
			node_data = await self.ZooKeeperClient.get_data(node_path)

		except aiozk.exc.NoNode:
			return None

		return node_data.decode(self.Encoding)


	async def list(self, path):
		recursive = path.endswith("*")

		if recursive:
			path = path[:-2]

		node_names = list()

		node_path = "{}/{}".format(self.LibraryBasePath, path)
		await self._list_by_node_path(node_path, node_names, recursive=recursive)

		return node_names


	async def _list_by_node_path(self, node_path, node_names, recursive=True):
		"""
		Recursive function to list all nested nodes within the ZooKeeper library.
		"""

		try:

			for node in await self.ZooKeeperClient.get_children(node_path):

				try:

					nested_node_path = "{}/{}".format(node_path, node)

					if recursive:
						await self._list_by_node_path(nested_node_path, node_names, recursive)

					# List only YAML files
					if not nested_node_path.endswith(".yaml"):
						continue

					# Remove library path from the beginning of node names
					node_names.append(
						nested_node_path.replace("{}/".format(self.LibraryBasePath), "")
					)

				except Exception as e:
					L.warning("Exception occurred during ZooKeeper load: '{}'".format(e))

		except aiozk.exc.NoNode:
			pass


	# async def write(self, path, data):
	# 	full_path = "{}/{}".format(self.LibraryBasePath, path)
	#
	# 	if await self.ZooKeeperClient.exists(full_path):
	# 		await self.ZooKeeperClient.delete(full_path)
	#
	# 	await self.ZooKeeperClient.create(full_path, data)


# class ModifyWatcher(BaseWatcher):
# 	"""
# 	ZooKeeper Watcher based on modify time change.
# 	"""
#
# 	watched_events = [
# 		aiozk.WatchEvent.CREATED,
# 		aiozk.WatchEvent.DATA_CHANGED
# 	]
#
#
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self.LastModified = None
#
#
# 	async def fetch(self, path):
# 		while True:
#
# 			try:
# 				data, stat = await self.client.get(path=path, watch=True)
# 				modified = stat.modified
#
# 				if self.LastModified != modified:
#
# 					if self.LastModified is not None:
# 						self.LastModified = modified
# 						return modified
#
# 					self.LastModified = modified
#
# 				await asyncio.sleep(10)
#
# 			except Exception as e:
# 				L.exception("During fetching modification time in ModifyWatcher, the following exception occurred: '{}'".format(e))
# 				await asyncio.sleep(10)
