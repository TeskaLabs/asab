import unittest
import collections
from asab.metrics.influxdb import influxdb_format
from asab.metrics.metrics import Counter, Gauge, Histogram


class TestInfluxDB(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestInfluxDB, self).__init__(*args, **kwargs)
		self.TestCounter = Counter("testcounter", tags={'help': 'This is a test counter.'})
		self.Now = 1234567890
		self.MetricNameTuple = collections.namedtuple("labels", ["method", "path", "status"])

	def test_influxdb_format(self):
		self.TestCounter.add("v1", 1, 0)
		self.TestCounter.add("v2", 24584, 0)
		counter_record = self.TestCounter.rest_get()
		mtree = {"dimension": counter_record}
		expected = "testcounter,help=This_is_a_test_counter. v1=1i 1234567890000000000\ntestcounter,help=This_is_a_test_counter. v2=24584i 1234567890000000000\n"
		self.assertEqual(expected, influxdb_format(mtree, self.Now))


	def test_influxdb_format_histogram(self):
		testHistogram = Histogram("testhistogram", [1, 10], tags={"host": "eliska"})
		testHistogram.set("some_name", 5)
		record = testHistogram.rest_get()
		mtree = {"dimension": record}
		expected = 'testhistogram,host=eliska,le=10.0 some_name=1i 1234567890000000000\ntesthistogram,host=eliska,le=inf some_name=1i 1234567890000000000\ntesthistogram,host=eliska Sum=5.0 1234567890000000000\ntesthistogram,host=eliska Count=1i 1234567890000000000\n'
		self.assertEqual(expected, influxdb_format(mtree, self.Now))

	def test_influxdb_format_bool(self):
		# https://stackoverflow.com/questions/37888620/comparing-boolean-and-int-using-isinstance
		testGauge = Gauge("testgauge", tags={'help': 'This is a test gauge.'})
		testGauge.set("v1", True)
		testGauge.set("v2", False)
		record = testGauge.rest_get()
		mtree = {"dimension": record}
		expected = 'testgauge,help=This_is_a_test_gauge. v1=t 1234567890000000000\ntestgauge,help=This_is_a_test_gauge. v2=f 1234567890000000000\n'
		self.assertEqual(expected, influxdb_format(mtree, self.Now))

	def test_influxdb_format_str(self):
		testGauge = Gauge("testgauge", tags={'help': 'This is a test gauge.'})
		testGauge.set("v1", "1")
		testGauge.set("v2", "hodně")
		record = testGauge.rest_get()
		mtree = {"dimension": record}
		expected = 'testgauge,help=This_is_a_test_gauge. v1="1" 1234567890000000000\ntestgauge,help=This_is_a_test_gauge. v2="hodně" 1234567890000000000\n'
		self.assertEqual(expected, influxdb_format(mtree, self.Now))
