import pprint
import asab
import asab.storage


asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'mongodb',
		},
		"mongo": {
			"uri": "192.168.64.14",
			"database": "test",
		}
	}
)


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

		object_id = await u.execute()


		# Executor runs in a transaction

		# Get the object by its id
		obj = await storage.get("test-collection", object_id)

		# Obtain upsertor object for update - specify existing `version` number
		u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v'])
		u.set("foo", "buzz")

		async with storage.transaction():
			object_id = await u.execute()


		# Abort transaction

		# Get the object by its id
		obj = await storage.get("test-collection", object_id)

		# Obtain upsertor object for update - specify existing `version` number
		u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v'])
		u.set("foo", "buzzA")

		async with storage.transaction() as tx:
			object_id = await u.execute()
			tx.abort()
		obj = await storage.get("test-collection", object_id)
		print("Attribute is not updated", obj['foo'])


		# See the results
		obj = await storage.get("test-collection", object_id)
		print(f"Result of get by id: {object_id}")
		pprint.pprint(obj)

		# Get collections
		print(await storage.collections())

		# Encrypt some data
		u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v'])
		# secret_message = "This is a super secret message!"
		# Convert the message to binary format before encrypting
		# u.set("super_secret", secret_message.encode("ascii"), encrypt=True)
		# object_id = await u.execute()

		# See the encrypted data
		# obj = await storage.get("test-collection", object_id)
		# print("Encrypted data: {}".format(obj.get("super_secret")))

		# See the decrypted data
		# obj = await storage.get("test-collection", object_id, decrypt=["super_secret"])
		# print("Decrypted data: {}".format(obj.get("super_secret")))

		# Test the StorageService.collection() method
		coll = await storage.collection("test-collection")
		cursor = coll.find({})
		print("Result of list")
		while await cursor.fetch_next:
			obj = cursor.next_object()
			pprint.pprint(obj)

		await storage.delete("test-collection", object_id)

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
