#!/usr/bin/env python3
import asab
import asab.api
import asab.zookeeper


L = asab.config.logging.getLogger(__name__)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		self.add_module(asab.zookeeper.Module)
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")


	async def main(self):
		zk_container = self.ZooKeeperService.DefaultContainer
		zk_client = zk_container.ZooKeeper

		path = zk_container.ZooKeeperPath + "/test"
		await zk_client.ensure_path(path)
		print("ensure_path completed")

if __name__ == '__main__':
	app = MyApplication()
	app.run()
