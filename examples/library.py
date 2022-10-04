#!/usr/bin/env python3
import os.path

import asab
import asab.library
import asab.zookeeper

asab.Config.add_defaults({
	"zookeeper": {
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181",
		"servers": "zookeeper-1:2181"
	},

	"library": {
		"azure_cache": "true",
	}

})


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__(modules=[asab.zookeeper.Module])

		# Specify a locations of the default library
		asab.Config["library"]["providers"] = '\n'.join([
			os.path.join(os.path.dirname(__file__), "library"),
			# "zk:///library",
			# "git+https://github.com/TeskaLabs/asab.git"
			"azure+https://lmio.blob.core.windows.net/library"
		])

		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

		# Continue only if the library is ready
		# We need to wait till eg. Zookeeper is connected
		self.PubSub.subscribe("ASABLibrary.ready!", self.on_library_ready)


	async def on_library_ready(self, event_name, library):
		items = await self.LibraryService.list("", recursive=True)
		print("# Library\n")
		for item in items:
			print(" *", item)
			if item.type == 'item':
				itemio = await self.LibraryService.read(item.name)
				if itemio is not None:
					with itemio:
						content = itemio.read()
						print("  - content: {}".format(len(content)))
				else:
					print("  - N/A")  # Item is likely disabled
		print("\n===")
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
