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

		self.Client = kazoo.client.KazooClient(
			hosts=hosts,
			connection_retry=kazoo.retry.KazooRetry(
				max_tries=-1,  # Try to reconnect indefinetively
			),
		)

		self.Client.add_listener(zkcnt._listener)


	async def _stop(self):
		ret = await self.ProactorService.execute(
			self.Client.stop,
		)
		return ret


	# read-only calls
	async def ensure_path(self, path):
		ret = await self.ProactorService.execute(
			self.Client.ensure_path, path
		)
		return ret

	async def exists(self, path):
		ret = await self.ProactorService.execute(
			self.Client.exists, path
		)
		return ret

	async def get_children(self, path):
		try:
			children = await self.ProactorService.execute(
				self.Client.get_children, path
			)
		except kazoo.exceptions.NoNodeError:
			# This is a silent error, it is indicated by None in the return
			return None
		return children


	async def get_data(self, path):
		try:
			data, stat = await self.ProactorService.execute(
				self.Client.get, path
			)
		except kazoo.exceptions.NoNodeError:
			# This is a silent error, it is indicated by None in the return
			return None
		return data

	# write methods
	async def set_data(self, path, data):
		try:
			ret = await self.ProactorService.execute(
				self.Client.set, path, data
			)
		except kazoo.exceptions.NoNodeError:
			L.warning("Failed to write the data. Reason: Node '{}' does not exist.".format(path))
			return None
		return ret

	async def delete(self, path, version=-1, recursive=False):
		try:
			ret = await self.ProactorService.execute(
				self.Client.delete, path, version, recursive
			)
		except kazoo.exceptions.NoNodeError:
			L.warning("Failed to delete node. Reason: Node '{}' does not exist.".format(path))
			return None
		return ret

	async def create(self, path, value, sequence=False, ephemeral=False, makepath=False):

		def do():
			return self.Client.create(path, value=value, ephemeral=ephemeral, sequence=sequence, makepath=makepath)

		return await self.ProactorService.execute(do)


	# create a new node or update the existing one
	async def upsert(self, path, value):
		def do():
			try:
				return self.Client.create(path, value=value)
			except kazoo.exceptions.NodeExistsError:
				return self.Client.set(path, value)

		return await self.ProactorService.execute(do)
