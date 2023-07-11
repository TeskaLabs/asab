---
author: Jakub Boukal
commit: 4db78e814d48f1911e1ce8df476f25be725764f0
date: 2019-12-10 17:55:51+01:00
title: Pubsub

---

!!! example

	```python title=pubsub.py linenums="1"
	#!/usr/bin/env python3
	import asab
	
	
	class MyApplication(asab.Application):
	
		async def initialize(self):
			self.PubSub.subscribe("Application.tick!", self.on_tick)
			self.d = DisapearingSubscriber()
			self.d_cnt = 3
			self.PubSub.subscribe("Application.tick!", self.d.on_non_ref)
			self.PubSub.subscribe("Application.tick!", FunctionalSubscriber)
	
	
		def on_tick(self, message_name):
			print(message_name)
			self.d_cnt -= 1
			if self.d_cnt == 0:
				self.d = None
	
	
	
	class DisapearingSubscriber(object):
	
		async def on_non_ref(self, message_name):
			print("DisapearingSubscriber: ", message_name)
	
	
	def FunctionalSubscriber(message_name):
		print("FunctionalSubscriber: ", message_name)
	
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
