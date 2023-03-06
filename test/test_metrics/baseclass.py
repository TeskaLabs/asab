import unittest

import asab
import asab.metrics
import asab.metrics.influxdb
from . import Module


class MetricsTestCase(unittest.TestCase):


	def setUp(self):
		super().setUp()
		asab.Config.add_defaults({
			"asab:metrics": {
				# We don't want native metrics to intervene with the unit test
				"native_metrics": "false",
			}
		})
		self.App = asab.Application(args=[], modules=[Module])
		self.MetricsService = self.App.get_service('asab.MockMetricsService')
		self.MetricsService.clear()
		self.MetricsService.Tags['host'] = "mockedhost.com"
		self.MockedLoop = MockedLoop()


class MockedLoop(object):
	def time(self):
		return 123.45
