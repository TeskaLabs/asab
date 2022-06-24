import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestGauge(MetricsTestCase):

	# There's no Gauge with dynamic tags

	def test_gauge_01(self):
		'''
		Gauge with init value
		'''
		gauge = self.MetricsService.create_gauge(
			"testgauge",
			init_values={"v1": 1},
			help='This is a test Gauge.'
		)

		# Test InfluxDB output with init values
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"testgauge,host=mockedhost.com v1=1i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(gauge.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testgauge gauge\n',
				'# HELP testgauge This is a test Gauge.\n',
				'testgauge{host="mockedhost.com",name="v1"} 1',
			])
		)

		gauge.set("v1", 2)
		gauge.set("v2", 4)
		self.MetricsService._flush_metrics()

		# Test InfluxDB output with init values
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"testgauge,host=mockedhost.com v1=2i,v2=4i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(gauge.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testgauge gauge\n',
				'# HELP testgauge This is a test Gauge.\n',
				'testgauge{host="mockedhost.com",name="v1"} 2\n',
				'testgauge{host="mockedhost.com",name="v2"} 4',
			])
		)



	def test_gauge_04(self):
		'''
		Gauge without init values
		'''
		gauge = self.MetricsService.create_gauge(
			"testgauge",
			help='This is a test Gauge.'
		)

		gauge.set("v1", 2)
		self.MetricsService._flush_metrics()

		# Test InfluxDB output with init values
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"testgauge,host=mockedhost.com v1=2i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(gauge.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testgauge gauge\n',
				'# HELP testgauge This is a test Gauge.\n',
				'testgauge{host="mockedhost.com",name="v1"} 2',
			])
		)
