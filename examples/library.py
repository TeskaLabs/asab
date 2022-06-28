#!/usr/bin/env python3
import asab
import asab.library
import asab.zookeeper
# Specify a default configuration
asab.Config.add_defaults(
	{
		"library": {
			# specify "servers": "..." here to provide addresses of Zookeeper servers
			"providers": "zk://10.17.164.239:2181,10.17.164.183:2181,10.17.169.210:2181/library"
		},
	}
)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		# Loading the ASAB Zookeeper module
		self.add_module(asab.zookeeper.Module)
		self.add_module(asab.library.Module)

	async def _on_zk_ready(self, event_name, zkcontainer):
		libsvc = self.get_service("asab.LibraryService")
		item = await libsvc.list("/", "default", recursive=True)
		print("Disabled paths are are follows...")
		print(item)

	async def main(self):
		self.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)



if __name__ == '__main__':
	app = MyApplication()
	app.run()
