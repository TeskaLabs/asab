import asab


class MyApplication(asab.Application):

	async def initialize(self):
		self.LibraryService = self.get_service("asab.LibraryService")
		self.PubSub.subscribe("Library.ready!", self.on_library_ready)
		self.PubSub.subscribe("Library.change!", self.on_library_change)

	async def on_library_ready(self, event_name, library=None):
		await self.LibraryService.subscribe("/Correlations/Microsoft/Windows/Account Created.yaml")

	def on_library_change(self, event_name, provider, path):
		print("Library item changed: {}".format(path))


if __name__ == "__main__":
	app = MyApplication()
	app.run()
