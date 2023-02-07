#!/usr/bin/env python3

import asab
import asab.library
import asab.zookeeper


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()
		asab.Config.read_string(
			"""
[library]
providers=git+https://github.com/TeskaLabs/asab.git
"""
		)
		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

		# Continue only if the library is ready
		self.PubSub.subscribe("ASABLibrary.ready!", self.on_library_ready)
		self.PubSub.subscribe("ASABLibrary.change!", self.on_library_change)


	async def on_library_ready(self, event_name, library=None):
		items = await self.LibraryService.list("", recursive=True)
		print("# Library\n")
		for item in items:
			print(" *", item)
		print("\n===")

		self.LibraryService.subscribe(["/asab"])

	def on_library_change(self, msg, provider, path):
		print("\N{rabbit} New changes in the library found by provider: '{}'".format(provider))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
