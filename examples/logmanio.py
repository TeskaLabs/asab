#!/usr/bin/env python3
import logging

import asab
import asab.logman
import asab.metrics


L = logging.getLogger(__name__)


class MyApplication(asab.Application):

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.logman.Module)
		logman_service = self.get_service('asab.LogManIOService')

		self.add_module(asab.metrics.Module)
		metrics_service = self.get_service('asab.MetricsService')
		self.Counter = metrics_service.create_counter("test_counter", init_values={'test_value': 0})

		logman_service.configure_metrics(metrics_service)
		logman_service.configure_logging(self)

		self.PubSub.subscribe("Application.tick!", self._on_tick)


	def _on_tick(self, event_name):
		L.warning("Tick: {}".format(event_name), struct_data={'key1': 'value1', 'key2': 2})
		self.Counter.add("test_value", 1)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
