import pprint

import asab
import asab.storage


asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'elasticsearch',
			'elasticsearch_url': 'https://localhost:9200/',
			# 'elasticsearch_api_key': 'RzNDVkc0a0JJdDJTS1JpMlFrSlc6SGdncDFJdFNRRE9HVEpvRGFwU2lsdw==',
			# 'elasticsearch_ssl_ca_file': '/home/mir/ca.crt',
			'elasticsearch_username': 'elastic',
			'elasticsearch_password': 'miraelena',
		}
	}
)


class MyApplication(asab.Application):

	async def initialize(self):

		# Loading the web service module
		self.add_module(asab.storage.Module)


	async def main(self):
		storage = self.get_service("asab.StorageService")


		connected = await storage.is_connected()
		if connected:
			print("Connected to ElasticSearch.")
		else:
			print("Connection failed.")

		# Obtain upsertor object which is associated with given "test-collection"
		# To create new object we keep default `version` to zero
		print("Creating default id and version")
		u = storage.upsertor("test-collection")
		u.set("bar", {"data": "test"})
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		print("Result of get by id '{}'".format(objid))
		pprint.pprint(obj)

		obj = await storage.get("test-collection", objid)
		# Obtain upsertor object for update - specify existing `version` number
		print("Specify version when updating")
		u = storage.upsertor("test-collection", obj_id=objid, version=obj['_v'])
		u.set("foo", "buzz")
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		print("Result of get by id '{}'".format(objid))
		pprint.pprint(obj)

		# Reindex the collection
		print("Reindexing the collection")
		await storage.reindex("test-collection", "test-collection-reindex")
		await storage.reindex("test-collection-reindex", "test-collection")


		obj = await storage.get("test-collection-reindex", objid)
		print("Result of get by id '{}'".format(objid))
		pprint.pprint(obj)

		# Remove the reindexed collection
		print("Deleting reindexed collection")
		await storage.delete("test-collection-reindex")

		# Delete the item
		await storage.delete("test-collection", objid)


		# Insert the document with provided ObjId
		print("Insert the document with provided ObjId")
		u = storage.upsertor("test-collection", "test")
		u.set("foo", "bar")
		objid = await u.execute()

		obj = await storage.get("test-collection", objid)
		print("Result of get by id '{}'".format(objid))
		pprint.pprint(obj)
		print("Delete the document with provided ObjId")
		await storage.delete("test-collection", objid)

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
