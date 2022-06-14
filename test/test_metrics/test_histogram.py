from .baseclass import MetricsTestCase
import asab.metrics.openmetric
import asab.metrics.influxdb


class TestHistogram(MetricsTestCase):


	def test_histogram_01(self):
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
		)
		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram_count{foo="bar",host="mockedhost.com"} 0\n',
				'testhistogram_sum{foo="bar",host="mockedhost.com"} 0.0'
			])
		)

		# Test Influx format with init values
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,foo=bar,host=mockedhost.com sum=0.0 123450000000\n',
				'testhistogram,foo=bar,host=mockedhost.com count=0i 123450000000\n',
			])
		)

		my_histogram.set('value1', 5)

		# Test OpenMetric output after set, before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram_count{foo="bar",host="mockedhost.com"} 0\n',
				'testhistogram_sum{foo="bar",host="mockedhost.com"} 0.0'
			])
		)

		self.MetricsService._flush_metrics()

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{foo="bar",host="mockedhost.com",le="10.0",value_name="value1"} 1\n',
				'testhistogram{foo="bar",host="mockedhost.com",le="100.0",value_name="value1"} 1\n',
				'testhistogram{foo="bar",host="mockedhost.com",le="inf",value_name="value1"} 1\n',
				'testhistogram_count{foo="bar",host="mockedhost.com"} 1\n',
				'testhistogram_sum{foo="bar",host="mockedhost.com"} 5.0',
			])
		)

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,foo=bar,host=mockedhost.com,le=10.0 value1=1i 123450000000\n',
				'testhistogram,foo=bar,host=mockedhost.com,le=100.0 value1=1i 123450000000\n',
				'testhistogram,foo=bar,host=mockedhost.com,le=inf value1=1i 123450000000\n',
				'testhistogram,foo=bar,host=mockedhost.com sum=5.0 123450000000\n',
				'testhistogram,foo=bar,host=mockedhost.com count=1i 123450000000\n',
			])
		)
