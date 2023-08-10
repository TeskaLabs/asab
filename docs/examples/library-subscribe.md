---
author: "Miroslav Bur\xFD\u0161ek"
commit: 0148e678ecf8f8fb81f6c0ef2b23deb2e306fdcb
date: 2023-06-13 14:56:00+02:00
title: Library subscribe

---

!!! example

	```python title='library-subscribe.py' linenums="1"
	#!/usr/bin/env python3
	
	import asab
	import asab.library
	import asab.zookeeper
	
	
	class MyApplication(asab.Application):
	
		def __init__(self):
	
			super().__init__()
			asab.Config["library"]["providers"] = "git+https://github.com/TeskaLabs/asab.git"
	
			self.LibraryService = asab.library.LibraryService(
				self,
				"LibraryService",
			)
	
			# Continue only if the library is ready
			self.PubSub.subscribe("Library.ready!", self.on_library_ready)
			self.PubSub.subscribe("Library.change!", self.on_library_change)
	
			# NOTE: Git Provider periodically pulls changes once per minute
	
	
		async def on_library_ready(self, event_name, library=None):
			items = await self.LibraryService.list("/", recursive=True)
			print("# Library\n")
			for item in items:
				print(" *", item)
			print("\n===")
	
			# Add subscription for changes in paths
			await self.LibraryService.subscribe(["/asab"])
	
		def on_library_change(self, msg, provider, path):
			print("\N{rabbit} New changes in the library found by provider: '{}'".format(provider))
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
