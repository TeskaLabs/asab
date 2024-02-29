#!/usr/bin/env python3
import os.path
import sys

import asab
import asab.zk_config
import asab.zookeeper

asab.Config.add_defaults({
	"zookeeper": {
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181",
		"servers": "10.173.34.137:2181",
		"path": "/asab"
	},

})


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__(modules=[asab.zookeeper.Module])

		# Locate the zookeeper service and initialize 'zookeeper'
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")
		self.ZooKeeperContainer = asab.zookeeper.ZooKeeperContainer(self.ZooKeeperService, "zookeeper")

		self.ConfigService = asab.zk_config.ConfigService(
			self,
			self.ZooKeeperContainer,
		)

		self.PubSub.subscribe("ASABConfig.ready!", self.on_config_ready)


	async def on_config_ready(self, _):
		types = await self.ConfigService.list_config_types()
		print("# Config types: \n")
		for type in types:
			print(type)
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()