import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestAggCounter(MetricsTestCase):


	def test_agg_counter_01(self):
		"""
		Resetable Aggregation Counter
		max
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0},
		)

		my_counter.set('value1', 20)
		my_counter.set('value1', 10)
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 30)

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=20i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 20\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_agg_counter_02(self):
		"""
		Resetable Aggregation Counter
		min
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 100, 'value2': 100},
			aggregator=min
		)

		my_counter.set('value1', 20)
		my_counter.set('value1', 10)
		self.MetricsService._flush_metrics()


		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=10i,value2=100i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 10\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 100',
			])
		)

	def test_agg_counter_03(self):
		"""
		Non-resetable Aggregation Counter
		max
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0},
			reset=False
		)

		my_counter.set('value1', 20)
		my_counter.set('value1', 10)
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 30)

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=20i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 30\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_agg_counter_04(self):
		"""
		Non-resetable Aggregation Counter
		min
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 100, 'value2': 100},
			aggregator=min,
			reset=False
		)

		my_counter.set('value1', 20)
		my_counter.set('value1', 10)
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 5)

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=10i,value2=100i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 5\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 100',
			])
		)
	def test_agg_counter_05(self):
		"""
		Resetable Aggregation Counter with dynamic tags
		with init values
		max
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			init_values={'value1': 0, 'value2': 0},
			dynamic_tags=True
		)

		my_counter.set('value1', 20, {'foo': 'bar'})
		my_counter.set('value1', 10, {'foo': 'bar'})
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 30, {'foo': 'bar'})

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=0i,value2=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value1=20i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",name="value1"} 0\n',
				'mycounter{host="mockedhost.com",name="value2"} 0\n',
				'mycounter{foo="bar",host="mockedhost.com",name="value1"} 20\n',
				'mycounter{foo="bar",host="mockedhost.com",name="value2"} 0',
			])
		)


	def test_agg_counter_06(self):
		"""
		Resetable Aggregation Counter with dynamic tags
		init_values
		min
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 100, 'value2': 100},
			aggregator=min,
			dynamic_tags=True
		)

		my_counter.set('value1', 20, {'tag': 'second'})
		my_counter.set('value1', 10, {'tag': 'second'})
		self.MetricsService._flush_metrics()


		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=100i,value2=100i 123450000000\n",
				"mycounter,tag=second,host=mockedhost.com,foo=bar value1=10i,value2=100i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 100\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 100\n',
				'mycounter{tag="second",host="mockedhost.com",foo="bar",name="value1"} 10\n',
				'mycounter{tag="second",host="mockedhost.com",foo="bar",name="value2"} 100',
			])
		)

	def test_agg_counter_07(self):
		"""
		Non-resetable Aggregation Counter with dynamic tags
		max
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			init_values={'value1': 0, 'value2': 0},
			reset=False,
			dynamic_tags=True
		)

		my_counter.set('value1', 20, {'foo': 'bar'})
		my_counter.set('value1', 10, {'foo': 'bar'})
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 30, {'foo': 'bar'})

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=0i,value2=0i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value1=20i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter counter\n',
				'mycounter_total{host="mockedhost.com",name="value1"} 0\n',
				'mycounter_total{host="mockedhost.com",name="value2"} 0\n',
				'mycounter_total{foo="bar",host="mockedhost.com",name="value1"} 30\n',
				'mycounter_total{foo="bar",host="mockedhost.com",name="value2"} 0',
			])
		)


	def test_agg_counter_08(self):
		"""
		Non-resetable Aggregation Counter with dynamic tags
		min
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			init_values={'value1': 100, 'value2': 100},
			aggregator=min,
			reset=False,
			dynamic_tags=True
		)

		my_counter.set('value1', 20, {'foo': 'bar'})
		my_counter.set('value1', 10, {'foo': 'bar'})
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 5, {'foo': 'bar'})

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=100i,value2=100i 123450000000\n",
				"mycounter,foo=bar,host=mockedhost.com value1=10i,value2=100i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter counter\n',
				'mycounter_total{host="mockedhost.com",name="value1"} 100\n',
				'mycounter_total{host="mockedhost.com",name="value2"} 100\n',
				'mycounter_total{foo="bar",host="mockedhost.com",name="value1"} 5\n',
				'mycounter_total{foo="bar",host="mockedhost.com",name="value2"} 100',
			])
		)

	def test_agg_counter_09(self):
		"""
		Resetable Aggregation Counter with dynamic tags
		w/o init_values
		max
		"""
		my_counter = self.MetricsService.create_aggregation_counter(
			"mycounter",
			dynamic_tags=True
		)

		my_counter.set('value1', 20, {'foo': 'bar'})
		my_counter.set('value1', 10, {'foo': 'bar'})
		self.MetricsService._flush_metrics()
		my_counter.set('value1', 30, {'foo': 'bar'})

		# Test InfluxDB

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=20i 123450000000\n",
			])
		)

		# Test OpenMetric
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{foo="bar",host="mockedhost.com",name="value1"} 20',
			])
		)
