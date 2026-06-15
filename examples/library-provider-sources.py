#!/usr/bin/env python3
import os.path

import asab
import asab.library


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		asab.Config["library"]["providers"] = "\n".join([
			os.path.join(os.path.dirname(__file__), "library"),
			"git+https://github.com/TeskaLabs/asab.git",
		])

		self.LibraryService = asab.library.LibraryService(
			self,
			"LibraryService",
		)

	async def main(self):
		print("# Library provider sources\n")
		for provider in self.LibraryService.Libraries:
			print("{} source ID '{}' for source '{}'".format(
				provider.__class__.__name__,
				provider.ID,
				provider.Source,
			))

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
