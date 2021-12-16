import json
import asyncio
import logging
import asab.zookeeper.builder

from ..config import ConfigObject

#

L = logging.getLogger(__name__)

#


class ZooKeeperContainer(ConfigObject):
	"""
	ZooKeeperContainer connects to Zookeeper via aiozk client:
	https://zookeeper.apache.org/
	https://pypi.org/project/aiozk/
	"""

	def __init__(self, app, config_section_name, config=None, z_path=None):
		super().__init__(config_section_name=config_section_name, config=config)
		'''
		Alternative 1) - Obtain Zookeeper container with config-section
		Alternative 2) - Obtain Zookeeper container with call z_path
		example : ZooKeeperContainer(app, config_section_name='', z_path=z_path)
		'''

		self.App = app
		self.ConfigSectionName = config_section_name
		self.ZooKeeper, self.ZooKeeperPath = asab.zookeeper.build_client(asab.Config, z_path)
		self.Advertisments = set()


	async def initialize(self, app):
		await self.ZooKeeper.start()
		await self.ZooKeeper.ensure_path(self.ZooKeeperPath)

		self.App.PubSub.subscribe("Application.tick/300!", self._do_advertise)
		self.App.PubSub.subscribe("ZooKeeper.advertise!", self._do_advertise)

		# Force advertisement immediatelly after initialization
		self.App.PubSub.publish("ZooKeeper.advertise!")


	async def finalize(self, app):
		await self.ZooKeeper.close()


	def advertise(self, data, path):
		self.Advertisments.add(
			ZooKeeperAdvertisement(self.ZooKeeperPath + path, data)
		)
		self.App.PubSub.publish("ZooKeeper.advertise!")


	async def _do_advertise(self, event_name):
		for adv in self.Advertisments:
			await adv._do_advertise(self)

	async def get_children(self):
		return await self.ZooKeeper.get_children(self.ZooKeeperPath)

	async def get_data(self, child, encoding="utf-8"):
		raw_data = await self.get_raw_data(child)
		if raw_data is None:
			return {}
		return json.loads(raw_data.decode(encoding))

	async def get_raw_data(self, child):
		return await self.ZooKeeper.get_data("{}/{}".format(self.ZooKeeperPath, child))


class ZooKeeperAdvertisement(object):

	def __init__(self, path, data):
		self.Path = path

		if isinstance(data, dict):
			self.Data = json.dumps(data).encode("utf-8")
		elif isinstance(data, str):
			self.Data = data.encode("utf-8")
		else:
			self.Data = data

		self.Node = None
		self.Lock = asyncio.Lock()


	async def _do_advertise(self, zoocontainer):
		async with self.Lock:
			if self.Node is not None and await zoocontainer.ZooKeeper.exists(self.Node):
				await zoocontainer.ZooKeeper.set_data(self.Node, self.Data)
				return

			self.Node = await zoocontainer.ZooKeeper.create(
				self.Path,
				data=self.Data,
				sequential=True,
				ephemeral=True
			)
