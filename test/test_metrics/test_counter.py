import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestCounter(MetricsTestCase):


	def test_counter_01(self):
		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		# Test InfluxDB output with init values
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value1"} 0\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value2"} 0',
			])
		)

		my_counter.add('value1', 1)

		# Test InfluxDB output before flush
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value1"} 0\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value2"} 0',
			])
		)

		self.MetricsService._flush_metrics()

		# Test InfluxDB output after flush
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=1i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value1"} 1\n',
				'mycounter{foo="bar",host="mockedhost.com",value_name="value2"} 0',
			])
		)
