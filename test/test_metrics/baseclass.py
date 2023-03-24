import unittest
import logging

import asab
import asab.abc
import asab.metrics
import asab.metrics.influxdb
from asab.metrics.service import MetricsService
from asab.metrics import Metric

L = logging.getLogger("__name__")



class MetricsTestCase(unittest.TestCase):

	def setUp(self):
		super().setUp()
		asab.Config.add_defaults({
			"asab:metrics": {
				# We don't want native metrics to intervene with the unit test
				"native_metrics": "false",
			}
		})
		self.App = asab.Application(args=[], modules=[])
		self.MetricsService = MockMetricsService(self.App, "asab.MetricsService")
		self.MetricsService.clear()
		self.MetricsService.Tags['host'] = "mockedhost.com"
		self.MetricsService.Tags['appclass'] = "mockappclass"
		self.MetricsService.Tags["instance_id"] = "test-instance-id-1"
		self.MockedLoop = MockedLoop()

	def tearDown(self):
		asab.abc.singleton.Singleton.delete(self.App.__class__)
		self.App = None
		root_logger = logging.getLogger()
		root_logger.handlers = []



class MockedLoop(object):
	def time(self):
		return 123.45


class MockApplication(object):
	# This is to test how the timestamp is created and saved to "measured_at", incl. duplicates testcase
	def time(self):
		return 123.45


class MockMetricsService(MetricsService):
	# This is to control metric's creation time and flush time
	def _add_metric(self, metric: Metric, metric_name: str, tags=None, reset=None, help=None, unit=None):
		# Add global tags
		metric.StaticTags.update(self.Tags)
		metric.App = MockApplication()

		# Add local static tags
		if tags is not None:
			metric.StaticTags.update(tags)


		metric._initialize_storage(
			self.Storage.add(metric_name, tags=metric.StaticTags.copy(), reset=reset, help=help, unit=unit)
		)
		self.Metrics.append(metric)

	def _flush_metrics(self):
		now = MockApplication().time() + 30  # This is to distinguish creation time from flush time

		self.App.PubSub.publish("Metrics.flush!")
		for metric in self.Metrics:
			try:
				metric.flush(now)
			except Exception:
				L.exception("Exception during metric.flush()")

		return now
