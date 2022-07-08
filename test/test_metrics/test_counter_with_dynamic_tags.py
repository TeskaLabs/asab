import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestCounterWithDynamicTags(MetricsTestCase):


	def test_counter_01(self):
		'''
		Resetable counter without init values and tags
		Dynamic tags used.
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
			dynamic_tags=True
		)

		my_counter.add('value1', 2, {"foo": "bar"})
		my_counter.sub('value1', 1, {"foo": "bar", "status": "200"})
		my_counter.sub('value2', 2, {"foo": "bar"})
		self.MetricsService._flush_metrics()

		# Openmetric, after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{foo="bar",host="mockedhost.com",name="value1"} 2\n',
				'mycounter_ages{foo="bar",host="mockedhost.com",name="value2"} -2\n',
				'mycounter_ages{foo="bar",status="200",host="mockedhost.com",name="value1"} -1',

			])
		)

		# InfluxDB after addition and flush
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=2i,value2=-2i 123450000000\n",
				"mycounter,foo=bar,status=200,host=mockedhost.com value1=-1i 123450000000\n",
			])
		)


	def test_counter_02(self):
		'''
		Non-resetable counter without init values and tags
		Dynamic tags used.
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
			reset=False,
			dynamic_tags=True
		)

		my_counter.add('value1', 2, {"foo": "bar"})
		self.MetricsService._flush_metrics()
		my_counter.sub('value1', 1, {"foo": "bar", "status": 200})
		my_counter.sub('value2', 2, {"foo": "bar"})
		my_counter.add('value1', 2, {"foo": "bar"})

		# Openmetric, after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages counter\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages_total{foo="bar",host="mockedhost.com",name="value1"} 4\n',
				'mycounter_ages_total{foo="bar",host="mockedhost.com",name="value2"} -2\n',
				'mycounter_ages_total{foo="bar",status="200",host="mockedhost.com",name="value1"} -1',

			])
		)

	def test_counter_03(self):
		'''
		Testing datatypes - float, bool, string
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
			dynamic_tags=True
		)

		my_counter.add('value1', 2.2, {"foo": "bar"})
		self.MetricsService._flush_metrics()

		# Openmetric FLOAT
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{foo="bar",host="mockedhost.com",name="value1"} 2.2',
			])
		)

		# InfluxDB FLOAT
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value1=2.2 123450000000\n",
			])
		)

		my_counter.add('value2', True, {"foo": "bar"})
		self.MetricsService._flush_metrics()

		# Openmetric BOOL is not supported by Prometheus - should be omitted
		# value expires after next flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!',
			])
		)

		# InfluxDB BOOL
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,foo=bar,host=mockedhost.com value2=t 123450000000\n",
			])
		)

		my_counter.add('value3', "nice_weather", {"foo": "bar"})
		self.MetricsService._flush_metrics()

		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!',
			])
		)


		# InfluxDB BOOL
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				'mycounter,foo=bar,host=mockedhost.com value3="nice_weather" 123450000000\n',
			])
		)
