import asab
import asab.metrics
import asab.metrics.influxdb
import asab.metrics.openmetric

from .baseclass import MetricsTestCase


class TestCounter(MetricsTestCase):


	def test_counter_01(self):
		"""
		Resetable counter with init values and tags
		Influx
		"""

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
				"mycounter,host=mockedhost.com,foo=bar value1=0i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 0\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)

		my_counter.add('value1', 1)
		self.MetricsService._flush_metrics()

		# Test InfluxDB output after flush
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=1i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 1\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_counter_02(self):
		"""
		Resetable counter with init values and tags
		Openmetric
		"""

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0}
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 0\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)

		my_counter.add('value1', 1)


		# Test OpenMetric output before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 0\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)

		self.MetricsService._flush_metrics()


		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter gauge\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value1"} 1\n',
				'mycounter{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_counter_03(self):
		"""
		Resetable counter with init values and tags, help and unit
		"""
		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0},
			help="Help!",
			unit="ages",
		)

		# Test InfluxDB output with init values
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=0i,value2=0i 123450000000\n",
			])
		)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{host="mockedhost.com",foo="bar",name="value1"} 0\n',
				'mycounter_ages{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)

		my_counter.add('value1', 1)
		self.MetricsService._flush_metrics()

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{host="mockedhost.com",foo="bar",name="value1"} 1\n',
				'mycounter_ages{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)


	def test_counter_04(self):
		'''
		Resetable counter without init values and tags
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
		)

		# Openmetric, before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!',
			])
		)

		# InfluxDB, before addition
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''
		)

		my_counter.add('value1', 1)
		self.MetricsService._flush_metrics()
		my_counter.sub('value1', 1)
		my_counter.sub('value2', 1)

		# Openmetric, after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{host="mockedhost.com",name="value1"} 1',
			])
		)

		# InfluxDB after addition and flush
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=1i 123450000000\n",
			])
		)



	def test_counter_05(self):
		'''
		Non-resetable Counter without init values and tags
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
			reset=False,
		)

		my_counter.add('value1', 2)
		self.MetricsService._flush_metrics()
		my_counter.sub('value1', 1)
		my_counter.add('value2', 2)

		# Openmetric, after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages counter\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages_total{host="mockedhost.com",name="value1"} 1\n',
				'mycounter_ages_total{host="mockedhost.com",name="value2"} 2',
			])
		)

		# InfluxDB after addition and flush
		# resetable or non-resetable - metrics are being sent to Influx only immediately after flush when fieldset.values == filedset.actuals
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=2i 123450000000\n",
			])
		)


	def test_counter_06(self):
		'''
		Non-resetable Counter with init values and tags
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			tags={'foo': 'bar'},
			init_values={'value1': 0, 'value2': 0},
			help="Help!",
			unit="ages",
			reset=False,
		)

		# Openmetric, after init
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages counter\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages_total{host="mockedhost.com",foo="bar",name="value1"} 0\n',
				'mycounter_ages_total{host="mockedhost.com",foo="bar",name="value2"} 0',
			])
		)

		# InfluxDB after init
		# resetable or non-resetable - metrics are being sent to Influx only immediately after flush when fieldset.values == filedset.actuals
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=0i,value2=0i 123450000000\n",
			])
		)

		my_counter.add('value1', 2)
		self.MetricsService._flush_metrics()
		my_counter.sub('value1', 1)
		my_counter.sub('value2', 2)

		# Openmetric, after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages counter\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages_total{host="mockedhost.com",foo="bar",name="value1"} 1\n',
				'mycounter_ages_total{host="mockedhost.com",foo="bar",name="value2"} -2',
			])
		)

		# InfluxDB after addition and flush
		# resetable or non-resetable - metrics are being sent to Influx only immediately after flush when fieldset.values == filedset.actuals
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com,foo=bar value1=2i,value2=0i 123450000000\n",
			])
		)


	def test_counter_07(self):
		'''
		Testing datatypes - float, bool, string
		'''

		my_counter = self.MetricsService.create_counter(
			"mycounter",
			help="Help!",
			unit="ages",
		)

		my_counter.add('value1', 2.2)
		self.MetricsService._flush_metrics()

		# Openmetric FLOAT
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_counter.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE mycounter_ages gauge\n',
				'# UNIT mycounter_ages ages\n',
				'# HELP mycounter_ages Help!\n',
				'mycounter_ages{host="mockedhost.com",name="value1"} 2.2',
			])
		)

		# InfluxDB FLOAT
		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			''.join([
				"mycounter,host=mockedhost.com value1=2.2 123450000000\n",
			])
		)

		my_counter.add('value2', True)
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
				"mycounter,host=mockedhost.com value2=t 123450000000\n",
			])
		)

		my_counter.add('value3', "nice_weather")
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
				'mycounter,host=mockedhost.com value3="nice_weather" 123450000000\n',
			])
		)
