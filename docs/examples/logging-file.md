---
author: "P\u0159emysl \u010Cern\xFD"
commit: cbb41483295e35fa3ab1b0169a249a30b51f8270
date: 2021-05-24 11:31:24+02:00
title: Logging file

---

!!! example

	```python title=logging-file.py linenums="1"
	#!/usr/bin/env python3
	import logging
	import asab
	
	#
	
	L = logging.getLogger(__name__)
	
	#
	
	
	class MyApplication(asab.Application):
		"""
		python3 logging-file.py -c ./data/logging-file.conf
		"""
	
		async def main(self):
			L.warning("Sample log WARNING!")
			L.error("Sample log ERROR!")
			self.stop()
	
	
	if __name__ == "__main__":
		app = MyApplication()
		app.run()
	
	```
