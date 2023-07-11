---
author: Ales Teska
commit: 0de7db994b4725059a738cc40683df32c6f3352f
date: 2022-06-13 20:17:49+02:00
title: Zookeeper advertise

---

!!! example

	```python title=zookeeper-advertise.py linenums="1"
	import asab
	import asab.api
	import asab.zookeeper
	
	
	# Advertisement through ApiService requires two configuration sections - `web` and `zookeeper`
	asab.Config.add_defaults(
		{
			"web": {
				"listen": "0.0.0.0 8088",
			},
			"zookeeper": {
				# specify "servers": "..." here to provide addresses of Zookeeper servers
				"path": "asab"
			},
		}
	)
	
	
	class MyApplication(asab.Application):
	
		def __init__(self):
			super().__init__(modules=[asab.web.Module, asab.zookeeper.Module])
	
			# Locate a Web Service
			self.WebService = self.get_service("asab.WebService")
	
			# Locate a ZooKeeper Service
			self.ZooKeeperService = self.get_service("asab.ZooKeeperService")
	
			# Initialize API service
			self.ApiService = asab.api.ApiService(self)
	
			# Introduce Web and ZooKeeper to API Service
			self.ApiService.initialize_web()
			self.ApiService.initialize_zookeeper()
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
