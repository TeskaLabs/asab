#!/usr/bin/env python3

"""
Simple app that watches global and tenant changes in library.
"""

import asab
import asab.library
import asab.zookeeper


asab.Config["library"]["providers"] = "zk:///library"
asab.Config["zookeeper"] = {
	"servers": "localhost:2181",
}


class MyApplication(asab.Application):

	def __init__(self):

		super().__init__()

		self.add_module(asab.zookeeper.Module)
		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

		# Continue only if the library is ready
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)
		self.PubSub.subscribe("Library.change!", self.on_library_change)


	async def on_library_ready(self, event_name, library=None):
		# Subscribe to global changes of Triangles directory
		await self.LibraryService.subscribe("/Triangles", target="global")
		# Subscribe to changes of Circles directory in any tenant
		await self.LibraryService.subscribe("/Circles", target="tenant")
		# Subscribe to changes of Squares directory in tenant "shapefactory"
		await self.LibraryService.subscribe("/Squares", target=("tenant", "shapefactory"))


	def on_library_change(self, msg, provider, path, target):
		print("\N{sparkles} New changes in directory {!r} in target {!r}.".format(path, target))


if __name__ == "__main__":
	app = MyApplication()
	app.run()
