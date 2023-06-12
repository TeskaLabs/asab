#!/usr/bin/env python3
import asab
import asab.library


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Specify the location of the library
		# The branch can be optionally specified in the URL fragment (after '#')
		# If the branch does not exist, KeyError is raised with the message: "reference 'refs/remotes/origin/...' not found"
		asab.Config["library"]["providers"] = "git+https://github.com/TeskaLabs/asab.git"

		# NOTE: If cloning from GitLab, use Deploy Tokens and specify the provider in format:
		# git+https://<username>:<deploy_token>@gitlab.com/john/awesome_project.git

		# The repository will be cloned to a temporary directory. You can optionally specify the path like this:
		# asab.Config["library:git"]["repodir"] = "/tmp/asab.provider.git/awesome_project"

		self.LibraryService = asab.library.LibraryService(self, "LibraryService")

		# Specify the directory path. It must start and end with "/"!
		self.Path = "/examples/data/"

		# Continue only if the library is ready
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)


	async def on_library_ready(self, event_name, library):

		items = await self.LibraryService.list(self.Path, recursive=True)

		print("=" * 10)
		print("# Testing Git provider with ASAB Library\n")
		print("The repository is cloned to a temporary directory: {}\n".format(self.LibraryService.Libraries[0].RepoPath))

		if self.LibraryService.Libraries[0].Branch is not None:
			print("On branch: {}\n".format(self.LibraryService.Libraries[0].Branch))
		else:
			print("On branch: master/main\n")

		if len(items) == 0:
			print("There are no items in directory {}!".format(self.Path))
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
