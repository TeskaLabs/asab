---
author: Ales Teska
commit: b4f862b4a414ed184ab7d9f27645934d07433860
date: 2023-07-11 20:25:43+02:00
title: Storage elasticsearch

---

!!! example

	```python title='storage_elasticsearch.py' linenums="1"
	import pprint
	
	import asab
	import asab.storage
	
	
	asab.Config.add_defaults(
		{
			'asab:storage': {
				'type': 'elasticsearch',
				'elasticsearch_url': 'https://localhost:9200/',  # enter one URL or list of URL's
				'elasticsearch_username': '<username>',
				'elasticsearch_password': '<password>',
				# 'elasticsearch_api_key': '<your api key>',
				# 'cafile': '<CA Certificate>',
			}
		}
	)
	
	
	class MyApplication(asab.Application):
	
		async def initialize(self):
	
			# Loading the web service module
			self.add_module(asab.storage.Module)
	
	
		async def main(self):
			storage = self.get_service("asab.StorageService")
			print("=" * 72)
	
			# Check the connection
			connected = await storage.is_connected()
			if connected:
				print("Connected to ElasticSearch on {}".format(storage.URL))
			else:
				print("Connection to {} failed".format(storage.URL))
	
			# Obtain upsertor object which is associated with given "test-collection"
			# To create new object we keep default `version` to zero
			print("-" * 72)
			print("Creating default id and version")
			u = storage.upsertor("test-collection")
			u.set("bar", {"data": "test"})
			object_id = await u.execute()
	
			obj = await storage.get("test-collection", object_id)
			print("-" * 72)
			print("Result of get by id '{}'".format(object_id))
			pprint.pprint(obj)
	
			# Obtain upsertor object for update - specify existing `version` number
			obj = await storage.get("test-collection", object_id)
			u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v'])
			print("-" * 72)
			print("Updating an object with ID '{}' and version {}".format(object_id, obj['_v']))
			u.set("foo", "buzz")
			object_id = await u.execute()
	
			obj = await storage.get("test-collection", object_id)
			print("-" * 72)
			print("Result of get by id '{}'".format(object_id))
			pprint.pprint(obj)
	
			# Reindex the collection
			print("-" * 72)
			print("Reindexing the collection")
			await storage.reindex("test-collection", "test-collection-reindex")
	
			obj = await storage.get("test-collection-reindex", object_id)
			print("-" * 72)
			print("Result of get by id '{}'".format(object_id))
			pprint.pprint(obj)
	
			# Remove the reindexed collection
			print("-" * 72)
			print("Deleting the entire reindexed collection")
			await storage.delete("test-collection-reindex")  # returns {'acknowledged': True}
	
			# Delete the item
			print("-" * 72)
			print("Deleting the object with ID {}".format(object_id))
			await storage.delete("test-collection", object_id)
	
	
			# Insert the document with provided ObjId
			print("-" * 72)
			print("Insert the document with ID 'test'")
			u = storage.upsertor("test-collection", "test")
			u.set("foo", "bar")
			object_id = await u.execute()
	
			obj = await storage.get("test-collection", object_id)
			print("-" * 72)
			print("Result of get by id '{}'".format(object_id))
			pprint.pprint(obj)
	
			print("-" * 72)
			print("Delete the document with provided ObjId")
			deleted_document = await storage.delete("test-collection", object_id)
	
			print("-" * 72)
			print("Deleted document:")
			pprint.pprint(deleted_document)
	
			print("=" * 72)
	
			self.stop()
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
