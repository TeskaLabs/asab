import pprint

import asab
import asab.storage


class MyApplication(asab.Application):

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.storage.Module)


	async def main(self):
		storage = self.get_service("asab.StorageService")

		u = storage.upsertor("test-collection")
		u.set("foo", "bar")
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		pprint.pprint(obj)

		await storage.delete("test-collection", objid)

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
