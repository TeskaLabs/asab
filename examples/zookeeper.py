#!/usr/bin/env python3
import asab
import asab.api
import asab.zookeeper

L = asab.config.logging.getLogger(__name__)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

	async def main(self):
		# TODO
		"""
		# Loading the zookeeper service module
		self.add_module(asab.zookeeper.Module)
		zksvc = self.get_service("asab.ZooKeeperService")
		zk_cont = zksvc.DefaultContainer
		zk_clinet = zk_cont.ZooKeeper
		zk_path = zk_cont.ZooKeeperPath
		zk_path = zk_path + "/Zookeeper_example"
		await zk_clinet.ensure_path(zk_path)
		await zk_clinet.set_data(zk_path, "Hello world!")
		await print(zk_clinet.get_data(zk_path))

	"""


if __name__ == '__main__':
	app = MyApplication()
	app.run()
