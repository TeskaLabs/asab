import asab
import asab.metrics
import asab.metrics.influxdb

from .baseclass import MetricsTestCase


class TestCounter(MetricsTestCase):


	def test_counter_01(self):
		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		# Test InfluxDB output with init values
		infludb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			infludb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)

		my_counter.add('value1', 1)

		# Test InfluxDB output before flush
		infludb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			infludb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)

		self.MetricsService._flush_metrics()

		# Test InfluxDB output after flush
		infludb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			infludb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=1i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value2=0i 123450000000\n",
			])
		)
