#!/usr/bin/env python3
import os.path
import pprint

import asab
import asab.library
from asab.library.schema import LibrarySchemaService


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Specify a location of the example library
		asab.Config["library"]["providers"] = os.path.join(os.path.dirname(__file__), "library")

		self.LibraryService = asab.library.LibraryService(self, "LibraryService")
		self.LibrarySchemaService = LibrarySchemaService(self, "LibrarySchemaService", self.LibraryService)

		self.PubSub.subscribe("Library.ready!", self.on_library_ready)

	async def on_library_ready(self, event_name, library):
		schema = await self.LibrarySchemaService.read_schema("/Schemas/ECS.yaml")
		print("Printing effective schema..")
		pprint.pprint(schema)
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
