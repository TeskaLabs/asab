import logging
import urllib.parse

import kazoo.client

#

L = logging.getLogger(__name__)

#


class KazooWrapper(object):
	"""
	This function builds ZooKeeper clients from Configs and urls
	urls supported :
	1. Absolute url.
	Example: zookeeper://zookeeper:12181/etc/configs/file1
	2. Relative ur1 with full path
		Example: zookeeper:///etc/configs/file1
		In this case the relative url is expanded as follows:
		zookeeper://{default_server}/etc/configs/file1
		Where {default_server} is substituted with the server entry of the [asab:zookeeper] configuration file section.
	3. Relative url with relative path
	Example: zookeeper:./etc/configs/file1
		In this case, the relative url is expanded as follows:
		zookeper://{default_server}/{default_path}/etc/configs/file1
		Where {default_server} is substituted with the "server" entry of the [asab:zookeeper] configuration file section and
		{default_path} is substituted with the "path" entry of the [asab:zookeeper] configuration file section.
	Sample config file:

	[asab.zookeeper]
	server=server1 server2 server3      <-- Default server
	path=/myfolder                      <-- Default path
	"""

	def __init__(self, app, config, z_url):

		from ..proactor import Module
		app.add_module(Module)
		self.ProactorService = app.get_service("asab.ProactorService")

		# initialize vaiables
		url_netloc = ''
		url_path = ''

		# Parse URL
		if z_url is not None:
			url_pieces = urllib.parse.urlparse(z_url)
			url_netloc = url_pieces.netloc
			url_path = url_pieces.path

		# If there is no location, use implied
		if url_netloc == '':
			url_netloc = config.get("servers")
			if url_netloc is None:
				# if server entry is missing exit
				L.error("Servers entry not passed in the configuration.")
				raise RuntimeError("Servers entry not passed in the configuration.")

		if url_path == '':
			url_path = config.get("path")
			# if path entry is missing retun with only client and path as none.
			if url_path is None:
				L.error("Path entry not passed in the configuration.")
				raise RuntimeError("Path entry not passed in the configuration.")

		if url_path.startswith("/"):
			url_path = url_path.strip("/")

		self.Path = url_path

		# Create and return the client and the url-path
		self.Client = kazoo.client.KazooClient(hosts=url_netloc)

	# connection start/close calls

	async def start(self):
		ret = await self.ProactorService.execute(
			self.Client.start,
		)
		return ret


	async def stop(self):
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
		children = await self.ProactorService.execute(
			self.Client.get_children, path
		)
		return children


	async def get_data(self, path):
		data, stat = await self.ProactorService.execute(
			self.Client.get, path
		)
		return data

	# write methods
	async def set_data(self, path, data):

		ret = await self.ProactorService.execute(
			self.Client.set, path, data
		)
		return ret

	async def delete(self, path):

		ret = await self.ProactorService.execute(
			self.Client.delete, path
		)
		return ret
