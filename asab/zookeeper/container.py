import aiozk
import asyncio
import json
from ..config import ConfigObject


class ZooKeeperContainer(ConfigObject):
	"""
	ZooKeeperContainer connects to Zookeeper via aiozk client:
	https://zookeeper.apache.org/
	https://pypi.org/project/aiozk/
	"""

	ConfigDefaults = {
		# Server list to which ZooKeeper Client tries connecting.
		# Specify a comma (,) separated server list.
		# A server is defined as address:port format.
		"servers": "zookeeper:12181",

		"path": "/asab",
	}

	def __init__(self, app, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)
		self.App = app
		self.ConfigSectionName = config_section_name
		self.ZooKeeper = aiozk.ZKClient(self.Config["servers"])
		self.ZooKeeperPath = self.Config["path"]

	async def initialize(self, app):
		await self.ZooKeeper.start()
		await self.ZooKeeper.ensure_path(self.ZooKeeperPath)
		await self.do_advertise(self)
		self.App.PubSub.subscribe("Application.tick/300!", self.on_tick)

	async def finalize(self, app):
		await self.ZooKeeper.close()

	async def advertise(self,data, path):
		self.Data =data
		self.Path = path
		print("Called advertise")
		await self.do_advertise(self)

	async def on_tick(self):
		self.do_advertise()

	async def do_advertise(self,encoding="utf-8"):
		if isinstance(self.Data, dict):
			data = json.dumps(self.Data).encode(encoding)
		elif isinstance(self.Data, str):
			data = self.Data.encode(encoding)
		elif asyncio.iscoroutinefunction(self.Data):
			data = await self.Data
		elif callable(self.Data):
			data = self.Data()

		return await self.ZooKeeper.create(
			"{}/{}".format(self.ZooKeeperPath, self.Path),
			data=data,
			sequential=True,
			ephemeral=True
		)

	async def get_children(self):
		return await self.ZooKeeper.get_children(self.ZooKeeperPath)

	async def get_data(self, child, encoding="utf-8"):
		raw_data = await self.get_raw_data(child)
		if raw_data is None:
			return {}
		return json.loads(raw_data.decode(encoding))

	async def get_raw_data(self, child):
		return await self.ZooKeeper.get_data("{}/{}".format(self.ZooKeeperPath, child))


