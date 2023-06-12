#!/usr/bin/env python3
import asab
import asab.library


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Specify the location of the library
		asab.Config["library"]["providers"] = "git+https://github.com/TeskaLabs/asab.git"

		self.LibraryService = asab.library.LibraryService(self, "LibraryService")

		self.Path = "/examples/data/"  # path to directory must start and end with "/"

		# Continue only if the library is ready
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)


	async def on_library_ready(self, event_name, library):
		items = await self.LibraryService.list(self.Path, recursive=True)

		print("=" * 10)
		print("# Testing git provider with ASAB Library\n")
		print("The repository is cloned to a temporary directory: {}".format(self.LibraryService.Libraries[0].RepoPath))
		print("=" * 10)

		if len(items) == 0:
			print("There are no items in directory {}!".format())
		else:
			print("Items:")

		for item in items:
			print("*", item.name)
			if item.type == 'item':
				itemio = await self.LibraryService.read(item.name)
				if itemio is not None:
					with itemio:
						content = itemio.read()
						print("  - content: {} bytes".format(len(content)))
				else:
					print("  - N/A")  # Item is likely disabled
		print("\n", "=" * 10, sep="")
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
