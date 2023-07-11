---
author: mejroslav
commit: 04a232b899de3bbe8c634361f5547865dea1a4c7
date: 2023-03-20 17:49:20+01:00
title: Storage elasticsearch

---

!!! example

	```python title=storage_elasticsearch.py linenums="1"
	import pprint
	
	import asab
	import asab.storage
	
	
	asab.Config.add_defaults(
		{
			'asab:storage': {
				'type': 'elasticsearch',
				'elasticsearch_url': 'http://localhost:9200/',
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
			await storage.reindex("test-collection", "test-collection-reindex")
			await storage.reindex("test-collection-reindex", "test-collection")
	
			# Remove the reindexed collection
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
	
	```
