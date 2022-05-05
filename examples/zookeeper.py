#!/usr/bin/env python3
import asab
import asab.api
import asab.zookeeper

L = asab.config.logging.getLogger(__name__)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		# Loading the zookeeper service module
		self.add_module(asab.zookeeper.Module)

		# Advertise self thru ZooKeeper
		zksvc = self.get_service("asab.ZooKeeperService")
		zksvc.DefaultContainer



if __name__ == "__main__":
	app = MyApplication()
	app.run()
