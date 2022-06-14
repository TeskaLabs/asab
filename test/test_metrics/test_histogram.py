from .baseclass import MetricsTestCase
import asab.metrics.openmetric


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
