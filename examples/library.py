#!/usr/bin/env python3
import asab
import asab.library
import asab.zookeeper

# Specify a default configuration
asab.Config.add_defaults(
	{
		"library": {
			# Note:
			# Pass parameters providers information of Zookeeper before running.
			# "providers": "",
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
		# tenant is None and recursive is set to True.
		final_list = await libsvc.list("/", None, True)
		print(final_list)

	async def main(self):
		self.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
