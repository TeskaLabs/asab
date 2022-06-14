import unittest

import asab
import asab.metrics
import asab.metrics.influxdb


class TestCounter(unittest.TestCase):


	def setUp(self) -> None:
		super().setUp()
		self.App = asab.Application(args=[], modules=[asab.metrics.Module])
		self.MetricsService = self.App.get_service('asab.MetricsService')

	def test_counter_01(self):
		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		my_counter.add('value1', 1)

		infludb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		print(">>", infludb_format)
