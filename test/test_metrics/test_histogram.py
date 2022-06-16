from .baseclass import MetricsTestCase
import asab.metrics.openmetric
import asab.metrics.influxdb


class TestHistogram(MetricsTestCase):

	def test_histogram_00(self):
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
		)

		expectation = {
			"name": "testhistogram",
			"type": "Histogram",
			"reset": True,
			"fieldset": [{
				"tags": {
					"host": "mockedhost.com",
					"foo": "bar",
				},
				"actuals": {
					"buckets": {
						1.0: {},
						10.0: {},
						100.0: {},
						float("inf"): {}
					},
					"sum": 0.0,
					"count": 0
				},
				"values": {
					"buckets": {
						1.0: {},
						10.0: {},
						100.0: {},
						float("inf"): {}
					},
					"sum": 0.0,
					"count": 0
				},
			}]
		}

		self.assertDictEqual(
			my_histogram.Storage,
			expectation,
		)

		my_histogram.set("v1", 2)
		self.MetricsService._flush_metrics()

		expectation = {
			"name": "testhistogram",
			"type": "Histogram",
			"reset": True,
			"fieldset": [{
				"tags": {
					"host": "mockedhost.com",
					"foo": "bar",
				},
				"actuals": {
					"buckets": {
						1.0: {},
						10.0: {},
						100.0: {},
						float("inf"): {}
					},
					"sum": 0.0,
					"count": 0
				},
				"values": {
					"buckets": {
						1.0: {},
						10.0: {"v1": 1},
						100.0: {"v1": 1},
						float("inf"): {"v1": 1}
					},
					"sum": 2.0,
					"count": 1
				},
			}]
		}

		self.assertDictEqual(
			my_histogram.Storage,
			expectation,
		)


	def test_histogram_01(self):
		# Influx
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
		)


		# Test Influx format with init values
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,host=mockedhost.com,foo=bar sum=0.0 123450000000\n',
				'testhistogram,host=mockedhost.com,foo=bar count=0i 123450000000\n',
			])
		)

		my_histogram.set('value1', 5)
		self.MetricsService._flush_metrics()

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,host=mockedhost.com,foo=bar,le=10.0 value1=1i 123450000000\n',
				'testhistogram,host=mockedhost.com,foo=bar,le=100.0 value1=1i 123450000000\n',
				'testhistogram,host=mockedhost.com,foo=bar,le=inf value1=1i 123450000000\n',
				'testhistogram,host=mockedhost.com,foo=bar sum=5.0 123450000000\n',
				'testhistogram,host=mockedhost.com,foo=bar count=1i 123450000000\n',
			])
		)



	def test_histogram_02(self):
		# Prometheus
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
				'testhistogram_count{host="mockedhost.com",foo="bar"} 0\n',
				'testhistogram_sum{host="mockedhost.com",foo="bar"} 0.0'
			])
		)

		my_histogram.set('value1', 5)

		# Test OpenMetric output after set, before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram_count{host="mockedhost.com",foo="bar"} 0\n',
				'testhistogram_sum{host="mockedhost.com",foo="bar"} 0.0'
			])
		)

		self.MetricsService._flush_metrics()

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{host="mockedhost.com",foo="bar",le="10.0",name="value1"} 1\n',
				'testhistogram{host="mockedhost.com",foo="bar",le="100.0",name="value1"} 1\n',
				'testhistogram{host="mockedhost.com",foo="bar",le="inf",name="value1"} 1\n',
				'testhistogram_count{host="mockedhost.com",foo="bar"} 1\n',
				'testhistogram_sum{host="mockedhost.com",foo="bar"} 5.0',
			])
		)
