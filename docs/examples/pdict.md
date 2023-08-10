---
author: Jakub Boukal
commit: b535454e6c89cf14ed8d21daeb4c45b6f8ec2945
date: 2019-12-20 16:46:01+01:00
title: Pdict

---

!!! example

	```python title='pdict.py' linenums="1"
	#!/usr/bin/env python3
	import os.path
	import asab
	
	
	class MyApplication(asab.Application):
	
		async def main(self):
			var_dir = asab.Config['general']['var_dir']
			pdict = asab.PersistentDict(os.path.join(var_dir, 'pdict.bin'))
	
			# Explicit load
			pdict.load()
			counter = pdict['counter'] = pdict.setdefault('counter', 0) + 1
			print("Executed for {} times".format(counter))
	
			# Explicit store
			pdict.store()
			self.stop()
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
