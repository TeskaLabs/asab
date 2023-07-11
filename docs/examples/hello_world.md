---
author: awichera
commit: ac71f28056ae26c0163f246d9b2b174a15d983fa
date: 2020-08-12 11:58:12+02:00
title: Hello world

---

!!! example

	```python title=hello_world.py linenums="1"
	#!/usr/bin/env python3
	import logging
	import asab
	
	L = logging.getLogger(__name__)
	
	
	class MyApplication(asab.Application):
		async def main(self):
			L.warning("Hello world!")
			self.stop()
	
	
	if __name__ == "__main__":
		app = MyApplication()
		app.run()
	
	```
