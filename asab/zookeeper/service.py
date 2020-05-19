import aiozk
import asyncio
import json

from ..abc.service import Service
from ..config import Config


class ZooKeeperService(Service):
	"""
	ZooKeeperService connects to Zookeeper via aiozk client:
	https://zookeeper.apache.org/
	https://pypi.org/project/aiozk/
	"""

	Config.add_defaults({
		"zookeeper": {
			"urls": "zookeeper:12181",
			"path": "/asab",
		}
	})

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.ZooKeeper = aiozk.ZKClient(Config["zookeeper"]["urls"])
		self.ZooKeeperPath = Config["zookeeper"]["path"]

	async def initialize(self, app):
		await self.ZooKeeper.start()
		await self.ZooKeeper.ensure_path(self.ZooKeeperPath)

	async def finalize(self, app):
		await self.ZooKeeper.close()

	async def advertise(self, data, encoding="utf-8"):
		if isinstance(data, dict):
			data = json.dumps(data).encode(encoding)
		elif isinstance(data, str):
			data = data.encode(encoding)
		elif asyncio.iscoroutinefunction(data):
			data = await data
		elif callable(data):
			data = data()

		return await self.ZooKeeper.create(
			"{}/i".format(self.ZooKeeperPath),
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
