import logging

import kazoo.retry
import kazoo.client
import kazoo.exceptions

#

L = logging.getLogger(__name__.rsplit(".", 1)[0])  # We want just "asab.zookeeper" in error messages

#


class KazooWrapper(object):


	def __init__(self, zkcnt, hosts):
		self.App = zkcnt.App
		self.ProactorService = zkcnt.ProactorService
		self.Stopped = False

		self.Client = kazoo.client.KazooClient(
			hosts=hosts,
			connection_retry=kazoo.retry.KazooRetry(
				max_tries=2,   # Two tries to connect / reconnect before giving up and going LOST
				ignore_expire=False,
			),
			command_retry=kazoo.retry.KazooRetry(
				max_tries=1,
				ignore_expire=False,
				max_delay=20,
			),
		)

		self.Client.add_listener(zkcnt._listener)


	# Read-only calls
	async def ensure_path(self, path):
		"""
		Recursively create a path if it does not exist.
		"""
		ret = await self.ProactorService.execute(
			self.Client.ensure_path, path
		)
		return ret


	async def exists(self, path):
		"""
		Check if a node exists.
		"""
		ret = await self.ProactorService.execute(
			self.Client.exists, path
		)
		return ret


	async def get(self, path):
		"""
		Get the data and stats from a node as a tuple. If the node does not exist, return `None`.

		Example:
		```python
		>>> data, stat = await zk.get("/path/to/node")
		>>> stat.ctime
		1700000000.0
		```
		"""
		try:
			data, stat = await self.ProactorService.execute(
				self.Client.get, path
			)
		except kazoo.exceptions.NoNodeError:
			# This is a silent error, it is indicated by None in the return
			return None, None
		return data, stat


	async def get_children(self, path):
		"""
		Get list of child nodes of a path. If the node does not exist, return `None`.
		"""
		try:
			children = await self.ProactorService.execute(
				self.Client.get_children, path
			)
		except kazoo.exceptions.NoNodeError:
			# This is a silent error, it is indicated by None in the return
			return None
		return children


	async def get_data(self, path):
		"""
		Get the data from a node. If the node does not exist, return `None`.
		"""
		try:
			data, stat = await self.ProactorService.execute(
				self.Client.get, path
			)
		except kazoo.exceptions.NoNodeError:
			# This is a silent error, it is indicated by None in the return
			return None
		return data

	# Write methods
	async def set_data(self, path, data):
		"""
		Set the data of a given node.
		"""
		try:
			ret = await self.ProactorService.execute(
				self.Client.set, path, data
			)
		except kazoo.exceptions.NoNodeError:
			L.warning("Failed to write the data. Reason: Node '{}' does not exist.".format(path))
			return None
		return ret

	async def delete(self, path, version=-1, recursive=False):
		"""
		Delete a node.
		"""
		try:
			ret = await self.ProactorService.execute(
				self.Client.delete, path, version, recursive
			)
		except kazoo.exceptions.NoNodeError:
			L.warning("Failed to delete node. Reason: Node '{}' does not exist.".format(path))
			return None
		return ret

	async def create(self, path, value, sequence=False, ephemeral=False, makepath=False):
		"""
		Create a new node with a value as its data.
		"""
		def do():
			return self.Client.create(path, value=value, ephemeral=ephemeral, sequence=sequence, makepath=makepath)

		return await self.ProactorService.execute(do)


	async def upsert(self, path, value):
		"""
		Update data for given path. If the node does not exist, create it.
		"""
		def do():
			try:
				return self.Client.set(path, value=value)
			except kazoo.exceptions.NoNodeError:
				try:
					return self.Client.create(path, value, makepath=True)
				except kazoo.exceptions.NodeExistsError:
					# Defense against race condition
					return self.Client.set(path, value=value)

		return await self.ProactorService.execute(do)
