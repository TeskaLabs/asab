import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestGauge(MetricsTestCase):

	def test_gauge_01(self):
		'''
		Gauge with init value
		'''
		gauge = self.MetricsService.create_gauge(
			"testgauge",
			init_values={"v1": 1},
			help='This is a test Gauge.'
		)

		gauge.set("v1", 2)
		self.MetricsService._flush_metrics()



	def test_gauge_02(self):
		'''
		Gauge with dynamic tags
		'''
		gauge = self.MetricsService.create_gauge(
			"testgauge",
			init_values={"v1": 1},
			help='This is a test Gauge.'
		)

		gauge.set("v1", 2, {"tag": "yes"})
		self.MetricsService._flush_metrics()


	def test_gauge_03(self):
		'''
		Gauge with static and dynamic tags
		'''
		gauge = self.MetricsService.create_gauge(
			"testgauge",
			init_values={"v1": 1},
			tags={"foo": "bar"},
			help='This is a test Gauge.'
		)

		gauge.set("v1", 2, {"tag": "yes"})
		self.MetricsService._flush_metrics()
