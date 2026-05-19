#!/usr/bin/env python3
import os.path
import pprint

import asab
import asab.library
import asab.zookeeper
from asab.library.schema import LibrarySchemaService

asab.Config.add_defaults({
	"zookeeper": {
		# "servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181",
		"servers": "zookeeper-1:2181"
	},

})


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__(modules=[asab.zookeeper.Module])

		# Specify a location of the example library
		asab.Config["library"]["providers"] = os.path.join(os.path.dirname(__file__), "library")

		self.LibraryService = asab.library.LibraryService(self, "LibraryService")
		self.LibrarySchemaService = LibrarySchemaService(self, "LibrarySchemaService", self.LibraryService)

		self.PubSub.subscribe("Library.ready!", self.on_library_ready)

	async def on_library_ready(self, event_name, library):
		schema = await self.LibrarySchemaService.read_schema("ECS")
		print("Printing effective schema..")
		pprint.pprint(schema)
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
