import unittest

import asab
import asab.metrics
import asab.metrics.influxdb


class MetricsTestCase(unittest.TestCase):

	def setUp(self) -> None:
		super().setUp()
		asab.Config.add_defaults({
			"asab:metrics": {
				# We don't want native metrics to intervene with the unit test
				"native_metrics": "false",
			}
		})
		self.App = asab.Application(args=[], modules=[asab.metrics.Module])
		self.MetricsService = self.App.get_service('asab.MetricsService')
		self.MetricsService.Tags['host'] = "mockedhost.com"
