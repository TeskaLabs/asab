import logging
import urllib.parse

import kazoo.client
import kazoo.exceptions

#

L = logging.getLogger(__name__.rsplit(".", 1)[0])  # We want just "asab.zookeeper" in error messages

#


class KazooWrapper(object):
	"""
	This function builds ZooKeeper clients from Configs and URLs

	Supported types of URLs:

	1. Absolute URL.
	Example: zookeeper://zookeeper:12181/etc/configs/file1

	2. Relative URL with full path
		Example: zookeeper:///etc/configs/file1
		In this case the relative url is expanded as follows:
		zookeeper://{default_server}/etc/configs/file1
		Where {default_server} is substituted with the server entry of the [zookeeper] configuration file section.

	3. Relative URL with relative path
	Example: zookeeper:./etc/configs/file1
		In this case, the relative URL is expanded as follows:
		zookeper://{default_server}/{default_path}/etc/configs/file1
		Where {default_server} is substituted with the "server" entry of the [zookeeper] configuration file section and
		{default_path} is substituted with the "path" entry of the [zookeeper] configuration file section.

	Sample config file:
	[asab.zookeeper]
	server=server1:port1,server2:port2,server3:port3
	path=myfolder
	"""

	def __init__(self, app, config, z_url):

		# Make sure that the proactor service exists
		from ..proactor import Module
		app.add_module(Module)
		self.ProactorService = app.get_service("asab.ProactorService")

		# Parse URL
		if z_url is not None:
			url_pieces = urllib.parse.urlparse(z_url)
			url_netloc = url_pieces.netloc
			url_path = url_pieces.path
		else:
			url_netloc = ''
			url_path = ''

		# If there is no location, use the value of 'servers' from the configuration
		if url_netloc == '':
			url_netloc = config.get("servers")
			if url_netloc == '' or url_netloc is None:
				# if server entry is missing exit
				L.critical("Cannot connect to Zookeeper, the configuration value of 'servers' not provided: '{}'".format(config))
				raise SystemExit("Exit due to a critical configuration error.")

		# If path has not been provided, use the value of 'path' from the configuration
		if url_path == '':
			url_path = config.get("path")

		# If path still has not been found (not in configuration), derive the path from the application class name
		if url_path == '' or url_path is None:
			url_path = app.__class__.__name__

		# Remove all heading '/' from path
		while url_path.startswith('/'):
			url_path = url_path[1:]

		self.Path = url_path.rstrip('/')
		self.Hosts = url_netloc

		# Create and return the client and the url-path
		self.Client = kazoo.client.KazooClient(hosts=self.Hosts)


	# connection start/close calls

	def _start(self):
		return self.Client.start()


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

	# create ephemeral node
	async def create(self, path, value, sequential, ephemeral):

		ret = await self.ProactorService.execute(
			self.Client.create, path, value, None, ephemeral, sequential, False)
		return ret
