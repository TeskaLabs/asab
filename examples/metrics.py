#!/usr/bin/env python3
import asab

class MyApplication(asab.Application):

	async def initialize(self):

		# Fake config file
		asab.Config.read_string("""
[asab:metrics]
target=influxdb

[asab:metrics:influxdb]
url=http://influxdb.lan:8086/
db=mydb
		""")

		from asab.metrics import Module
		self.add_module(Module)

		self.MetricsService = self.get_service('asab.MetricsService')

		# The timer will trigger a message publishing at every second
		self.PubSub.subscribe("Application.tick!", self.on_tick)


	async def on_tick(self, event_type):
		print("Tick!")
		self.MetricsService.add('test', {'v1': 1, 'v2': 3}, tags={'foo':'bar'})


if __name__ == '__main__':
	app = MyApplication()
	app.run()

