import pprint

import asab
import asab.storage


'''
../etc/site.conf

[asab:storage]
type=mongodb

'''
class MyApplication(asab.Application):

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.storage.Module)


	async def main(self):
		storage = self.get_service("asab.StorageService")

		# Obtain upsertor object which is associated with given "test-collection"
		# To create new object we keep default `version` to zero
		u = storage.upsertor("test-collection")
		u.set("foo", "bar")
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		# Obtain upsertor object for update - specify existing `version` number
		u = storage.upsertor("test-collection", obj_id=objid, version=obj['_v'])
		u.set("foo", "buzz")
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		print(f"Result of get by id: {objid}")
		pprint.pprint(obj)

		coll = await storage.collection("test-collection")
		cursor = coll.find({})
		print("Result of list")
		while await cursor.fetch_next:
			obj = cursor.next_object()
			pprint.pprint(obj)

		await storage.delete("test-collection", objid)

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
