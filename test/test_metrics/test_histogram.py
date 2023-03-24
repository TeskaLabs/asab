from .baseclass import MetricsTestCase
import asab.metrics.openmetric
import asab.metrics.influxdb


class TestHistogram(MetricsTestCase):

	def test_histogram_01(self):
		"""
		Influx
		"""
		self.maxDiff = None
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
		)

		# Test Influx format with init values
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''
		)

		my_histogram.set('value1', 5)
		self.MetricsService._flush_metrics()

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=10.0 value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=100.0 value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=inf value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar sum=5.0 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar count=1i 153450000000\n',
			])
		)



	def test_histogram_02(self):
		"""
		Prometheus
		"""
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
				'# TYPE testhistogram histogram',
			])
		)

		my_histogram.set('value1', 5)

		# Test OpenMetric output after set, before flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram',
			])
		)

		self.MetricsService._flush_metrics()

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value1"} 1\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value1"} 1\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value1"} 1\n',
				'testhistogram_count{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 1\n',
				'testhistogram_sum{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 5.0',
			])
		)


	def test_histogram_03(self):
		"""
		Non-resetable histogram
		Openmetric
		"""

		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
			reset=False
		)

		my_histogram.set('value1', 5)
		self.MetricsService._flush_metrics()
		my_histogram.set('value1', 3.5)

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=10.0 value1=1i 123450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=100.0 value1=1i 123450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=inf value1=1i 123450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar sum=5.0 123450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar count=1i 123450000000\n',
			])
		)

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value1"} 2\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value1"} 2\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value1"} 2\n',
				'testhistogram_count{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 2\n',
				'testhistogram_sum{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 8.5',
			])
		)


	def test_histogram_04(self):
		"""
		Resetable histogram
		with dynamic tags
		"""
		self.maxDiff = None
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
			dynamic_tags=True
		)

		my_histogram.set('value1', 5, {"tag": "yes"})
		self.MetricsService._flush_metrics()

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=10.0 value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=100.0 value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=inf value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar sum=5.0 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar count=1i 123450000000\n',
			])
		)

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value1"} 1\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value1"} 1\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value1"} 1\n',
				'testhistogram_count{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 1\n',
				'testhistogram_sum{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 5.0',
			])
		)


	def test_histogram_05(self):
		"""
		Non-resetable histogram
		with dynamic tags
		"""
		self.maxDiff = None
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
			reset=False,
			dynamic_tags=True
		)

		my_histogram.set('value1', 5, {"tag": "yes"})
		self.MetricsService._flush_metrics()
		my_histogram.set('value2', 5, {})
		my_histogram.set('value2', 50, {})

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=10.0 value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=100.0 value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=inf value1=1i 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar sum=5.0 123450000000\n',
				'testhistogram,tag=yes,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar count=1i 123450000000\n',
			])
		)

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram histogram\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value1"} 1\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value1"} 1\n',
				'testhistogram{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value1"} 1\n',
				'testhistogram_count{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 1\n',
				'testhistogram_sum{tag="yes",hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 5.0\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value2"} 1\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value2"} 2\n',
				'testhistogram{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value2"} 2\n',
				'testhistogram_count{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 2\n',
				'testhistogram_sum{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 55.0',

			])
		)


	def test_histogram_06(self):
		"""
		Help and units
		"""
		my_histogram = self.MetricsService.create_histogram(
			"testhistogram",
			[1, 10, 100],
			tags={'foo': 'bar'},
			help="This is a testing histogram.",
			unit="seconds"
		)

		my_histogram.set('value1', 5)
		self.MetricsService._flush_metrics()

		# Test Influx format output after flush
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=10.0 value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=100.0 value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar,le=inf value1=1i 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar sum=5.0 153450000000\n',
				'testhistogram,hostname=mockedhost.com,appclass=mockappclass,instance_id=test/instance/id,foo=bar count=1i 153450000000\n',
			])
		)

		# Test OpenMetric output after flush
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_histogram.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testhistogram_seconds histogram\n',
				'# UNIT testhistogram_seconds seconds\n',
				'# HELP testhistogram_seconds This is a testing histogram.\n',
				'testhistogram_seconds{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="10.0",name="value1"} 1\n',
				'testhistogram_seconds{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="100.0",name="value1"} 1\n',
				'testhistogram_seconds{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar",le="inf",name="value1"} 1\n',
				'testhistogram_seconds_count{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 1\n',
				'testhistogram_seconds_sum{hostname="mockedhost.com",appclass="mockappclass",instance_id="test/instance/id",foo="bar"} 5.0',
			])
		)
