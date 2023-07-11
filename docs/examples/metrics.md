---
author: eliska
commit: 3c9b1d9774c791af8f47a7a5b06bd427c081eab8
date: 2022-06-27 12:27:14+02:00
title: Metrics

---

!!! example

	```python title=metrics.py linenums="1"
	#!/usr/bin/env python3
	import asab
	import asab.web
	import asab.metrics
	import asab.api
	
	# Advertisement through ApiService requires two configuration sections - `web` and `zookeeper`
	asab.Config.add_defaults(
		{
			"web": {
				"listen": "0.0.0.0 8089",
			},
			"asab:metrics": {
				"target": "influxdb"
			},
			"asab:metrics:influxdb": {
				"url": "http://localhost:8086/",
				"db": "test",
				"username": "test",
				"password": "testtest",
			}
		}
	)
	
	
	class MyApplication(asab.Application):
	
		def __init__(self):
			super().__init__(modules=[asab.web.Module, asab.metrics.Module])
	
			metrics_service = self.get_service('asab.MetricsService')
			self.MyCounter = metrics_service.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})
			self.MyGauge = metrics_service.create_gauge("mygauge", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})
			self.MyEPSCounter = metrics_service.create_eps_counter("myepscounter", tags={'foo': 'bar'}, init_values={'event.in': 0})
	
			# The timer will trigger a message publishing at every second
			self.PubSub.subscribe("Application.tick!", self.on_tick)
	
			# Initialize API service
			self.ApiService = asab.api.ApiService(self)
			self.ApiService.initialize_web()
	
	
		async def on_tick(self, event_type):
			print("Tick!")
			self.MyCounter.add('v1', 1)
			self.MyGauge.set('v1', 1)
			self.MyEPSCounter.add('event.in', 1)
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
