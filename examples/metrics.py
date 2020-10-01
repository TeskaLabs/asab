#!/usr/bin/env python3
import asab


class MyApplication(asab.Application):

	async def initialize(self):

		# Fake config file
		asab.Config.read_string("""
[asab:metrics]
target=influxdb

[asab:metrics:influxdb]
url=http://localhost:8086/
db=mydb
		""")

		from asab.metrics import Module
		self.add_module(Module)

		metrics_service = self.get_service('asab.MetricsService')
		self.MyCounter = metrics_service.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})
		self.MyGauge = metrics_service.create_gauge("mygauge", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})
		self.MyEPSCounter = metrics_service.create_eps_counter("myepscounter", tags={'foo': 'bar'}, init_values={'event.in': 0})

		# The timer will trigger a message publishing at every second
		self.PubSub.subscribe("Application.tick!", self.on_tick)


	async def on_tick(self, event_type):
		print("Tick!")
		self.MyCounter.add('v1', 1)
		self.MyGauge.set('v1', 1)
		self.MyEPSCounter.add('event.in', 1)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
