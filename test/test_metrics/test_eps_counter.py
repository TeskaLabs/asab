import time

import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestEPSCounter(MetricsTestCase):


	def test_eps_counter_01(self):
		"""
		Resetable EPS Counter
		"""
		my_counter = self.MetricsService.create_eps_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		time.sleep(.250)
		self.MetricsService._flush_metrics()

		my_counter.add('value1', 20)
		time.sleep(.250)
		self.MetricsService._flush_metrics()

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		value = my_counter.Storage.get("fieldset")[0].get("values").get("value1")
		self.assertNotEqual(value, 0)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1={}i,value2=0i 123450000000\n".format(value),
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} ' + '{}\n'.format(value),
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_eps_counter_02(self):
		"""
		Non-resetable EPS Counter
		"""
		my_counter = self.MetricsService.create_eps_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0},
			reset=False
		)

		time.sleep(.250)
		self.MetricsService._flush_metrics()

		my_counter.add('value1', 20)
		time.sleep(.250)
		self.MetricsService._flush_metrics()

		my_counter.add('value1', 20)
		time.sleep(.250)
		self.MetricsService._flush_metrics()

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		value = my_counter.Storage.get("fieldset")[0].get("values").get("value1")
		self.assertNotEqual(value, 0)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1={}i,value2=0i 123450000000\n".format(value),
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} ' + '{}\n'.format(value),
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)
