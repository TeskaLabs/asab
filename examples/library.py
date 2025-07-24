#!/usr/bin/env python3
import os.path
import asyncio

import asab
import asab.exceptions
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
			"git+https://github.com/TeskaLabs/asab.git"
		])

		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

		# Continue only if the library is ready
		# We need to wait till eg. Zookeeper is connected
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)

		self.Event = asyncio.Event()


	async def on_library_ready(self, event_name, library):
		try:
			items = await self.LibraryService.list("/", recursive=False)
		except asab.exceptions.LibraryNotReadyError:
			return

		print("# Library\n")
		for item in items:
			print(" *", item)
			if item.type == 'item':
				try:
					async with self.LibraryService.open(item.name) as item_io:
						if item_io is not None:
							item_bytes = item_io.read()  # can be decoded with utf-8
							print("  - content: {} bytes".format(len(item_bytes)))
						else:
							print("  - N/A")  # Item is likely disabled
				except asab.exceptions.LibraryNotReadyError as err:
					print("  - !!! Failed to open {}: {}".format(item.name, err))
				except asab.exceptions.LibraryError as err:
					print("  - !!! Cannot open {} (not ready): {}".format(item.name, err))

		print("\n===")
		self.Event.set()


	async def main(self):
		await self.Event.wait()
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
