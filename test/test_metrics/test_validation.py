import asab
import asab.metrics
import asab.metrics.influxdb

from .baseclass import MetricsTestCase


class TestValidation(MetricsTestCase):
	def test_validation_01(self):
		"""
		Tests if the name validation works
		Influx
		"""

		self.MetricsService.create_counter(
			"my, count er",
			tags={"foo": "bar"},
			init_values={"value1": 0, "value2": 0},
		)

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			"".join(
				[
					"my\\,\\ count\\ er,host=mockedhost.com,foo=bar value1=0i,value2=0i 123450000000\n",
				]
			),
		)


	def test_validation_02(self):
		"""
		Tests if the tag validation works
		Influx
		"""

		self.MetricsService.create_counter(
			"mycounter",
			tags={"fo, = o": "ba, = r"},
			init_values={"value1": 0, "value2": 0},
		)

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			"".join(
				[
					"mycounter,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r value1=0i,value2=0i 123450000000\n",
				]
			),
		)


	def test_validation_03(self):
		"""
		Tests if the field/values validation works
		Influx
		"""

		self.MetricsService.create_counter(
			"mycounter",
			tags={"foo": "bar"},
			init_values={"val, ue1": 0, "va,lue 2": 0},
		)

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			"".join(
				[
					"mycounter,host=mockedhost.com,foo=bar val\\,\\ ue1=0i,va\\,lue\\ 2=0i 123450000000\n",
				]
			),
		)


	def test_validation_04(self):
		"""
		Tests if the field/values validation works but with the value being a string
		Influx
		"""

		self.MetricsService.create_counter(
			"mycounter",
			tags={"foo": "bar"},
			init_values={"value1": "te\\st\"1", "value2": "\"test\" 2"},
		)

		influxdb_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influxdb_format,
			"".join(
				[
					'mycounter,host=mockedhost.com,foo=bar value1="te\\\\st\\\"1",value2="\\\"test\\\" 2" 123450000000\n',
				]
			),
		)


	def test_validation_05(self):
		"""
		Tests if the validation works in a histogram
		Influx
		"""
		self.maxDiff = None
		my_histogram = self.MetricsService.create_histogram(
			"test histo,gram",
			[1, 10, 100],
			tags={"fo, = o": "ba, = r"},
		)

		my_histogram.set('value1', 5)

		self.MetricsService._flush_metrics()
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'test\\ histo\\,gram,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r,le=10.0 value1=1i 123450000000\n',
				'test\\ histo\\,gram,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r,le=100.0 value1=1i 123450000000\n',
				'test\\ histo\\,gram,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r,le=inf value1=1i 123450000000\n',
				'test\\ histo\\,gram,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r sum=5.0 123450000000\n',
				'test\\ histo\\,gram,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r count=1i 123450000000\n',
			])
		)
