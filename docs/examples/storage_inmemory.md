---
author: mejroslav
commit: 04a232b899de3bbe8c634361f5547865dea1a4c7
date: 2023-03-20 17:49:20+01:00
title: Storage inmemory

---

!!! example

	```python title=storage_inmemory.py linenums="1"
	import pprint
	
	import asab
	import asab.storage
	
	
	asab.Config.add_defaults(
		{
			'asab:storage': {
				'type': 'inmemory',
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
			objid = await u.execute()
	
			obj = await storage.get("test-collection", objid)
			# Obtain upsertor object for update - specify existing `version` number
			u = storage.upsertor("test-collection", obj_id=objid, version=obj['_v'])
			u.set("foo", "buzz")
			objid = await u.execute()
	
			obj = await storage.get("test-collection", objid)
			print(f"Result of get by id: {objid}")
			pprint.pprint(obj)
	
			await storage.delete("test-collection", objid)
	
			self.stop()
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
