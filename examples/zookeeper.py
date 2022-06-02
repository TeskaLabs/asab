#!/usr/bin/env python3
import asab
import asab.zookeeper


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		# Loading the ASAB Zookeeper module
		self.add_module(asab.zookeeper.Module)

		# Locate the Zookeeper service
		zksvc = self.get_service("asab.ZooKeeperService")

		# Create the Zookeeper container
		self.ZkContainer = asab.zookeeper.ZooKeeperContainer(
			zksvc, 'my:zk',
			config={
				"servers": "10.17.164.239:2181,10.17.164.183:2181,10.17.169.210:2181",
				"path": "asab"
			}
		)

		# Subscribe to the event that indicated the successful connection to the Zookeeper server(s)
		self.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)


	async def _on_zk_ready(self, event_name, zkcontainer):
		# If there is more than one ZooKeeper Container being initialized, this method is called at every Container initialization.
		# Then you need to check whether the specific ZK Container has been initialized.
		if zkcontainer == self.ZkContainer:
			path = self.ZkContainer.ZooKeeperPath + "/hello"
			await self.ZkContainer.ZooKeeper.ensure_path(path)
			print("The path in Zookeeper has been created.")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
