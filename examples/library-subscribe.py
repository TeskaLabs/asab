#!/usr/bin/env python3

import asab
import asab.library
import asab.zookeeper


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__(modules=[asab.zookeeper.Module])



		asab.Config.read_string(
			"""
[library]
providers=zk://192.168.64.4:2181/library
"""
		)

		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

		# Continue only if the library is ready
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)
		self.PubSub.subscribe("Library.change!", self.on_library_change)


	async def on_library_ready(self, event_name, library=None):
		items = await self.LibraryService.list("/", recursive=True)
		print("# Library\n")
		for item in items:
			print(" *", item)
		print("\n===")

		await self.LibraryService.subscribe(["/Site"])

	def on_library_change(self, msg, provider, path):
		print("\N{rabbit} New changes in the library found by provider: '{}'".format(provider))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
