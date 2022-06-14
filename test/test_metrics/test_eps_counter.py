import time

import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestEPSCounter(MetricsTestCase):


	def test_eps_counter_01(self):
		my_counter = self.MetricsService.create_eps_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		time.sleep(.250)
		self.MetricsService._flush_metrics()

		my_counter.add('value1', 200)
		time.sleep(.250)
		self.MetricsService._flush_metrics()

