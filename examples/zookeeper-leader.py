#!/usr/bin/env python3
import asab
import asab.zookeeper

# Specify a default configuration
asab.Config.add_defaults(
	{
		"my:zk": {
			# specify "servers": "..." here to provide addresses of Zookeeper servers
			"servers": "fu01:2181,fu02:2181,fu03:2181",
			"path": "ateska2607",
			"timeout": "30",
		},
	}
)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		# Loading the ASAB Zookeeper module
		self.add_module(asab.zookeeper.Module)

		# Locate the Zookeeper service
		zksvc = self.get_service("asab.ZooKeeperService")

		# Create the Zookeeper container
		self.ZkContainer = asab.zookeeper.ZooKeeperContainer(zksvc, 'my:zk')

		self.LeaderService = asab.zookeeper.LeaderService(self, self.ZkContainer, 'example-leader')

		# Subscribe to the event that indicated the successful connection to the Zookeeper server(s)
		self.PubSub.subscribe("LeaderService.state/LEADER!", self._on_leader)
		self.PubSub.subscribe("LeaderService.state/FOLLOWER!", self._on_follower)


	def _on_leader(self, event_name, leader_name):
		print("I am the leader at {} election".format(leader_name))
		print("Leader info: {}".format(self.LeaderService.LeaderInfo))

	def _on_follower(self, event_name, leader_name):
		print("I am a follower at '{}' election".format(leader_name))
		print("Leader info: {}".format(self.LeaderService.LeaderInfo))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
