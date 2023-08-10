---
author: Ales Teska
commit: 96255ea5fe472f3485a894512a0e74ba20032698
date: 2022-06-10 15:24:33+02:00
title: Zookeeper

---

!!! example

	```python title='zookeeper.py' linenums="1"
	#!/usr/bin/env python3
	import asab
	import asab.zookeeper
	
	# Specify a default configuration
	asab.Config.add_defaults(
		{
			"my:zk": {
				# specify "servers": "..." here to provide addresses of Zookeeper servers
				"path": "asab"
			},
		}
	)
	
	
	class MyApplication(asab.Application):
	
	
		def __init__(self):
			super().__init__()
	
			# Loading the ASAB Zookeeper module
			self.add_module(asab.zookeeper.Module)
	
			# Locate the Zookeeper service
			zksvc = self.get_service("asab.ZooKeeperService")
	
			# Create the Zookeeper container
			self.ZkContainer = asab.zookeeper.ZooKeeperContainer(zksvc, 'my:zk')
	
			# Subscribe to the event that indicated the successful connection to the Zookeeper server(s)
			self.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)
	
	
		async def _on_zk_ready(self, event_name, zkcontainer):
			# If there is more than one ZooKeeper Container being initialized, this method is called at every Container initialization.
			# Then you need to check whether the specific ZK Container has been initialized.
			if zkcontainer == self.ZkContainer:
				path = self.ZkContainer.ZooKeeperPath + "/hello"
				await self.ZkContainer.ZooKeeper.ensure_path(path)
				print("The path in Zookeeper has been created.")
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
