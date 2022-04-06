import unittest
import collections
from asab.metrics.influxdb import influxdb_format
from asab.metrics.metrics import Counter


class TestInfluxDB(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestInfluxDB, self).__init__(*args, **kwargs)
		self.TestCounter = Counter("testcounter", tags={'help': 'This is a test counter.'})
		self.Now = 1234567890
		self.MetricNameTuple = collections.namedtuple("labels", ["method", "path", "status"])

	def test_influxdb_format(self):
		values = {'v1': 1, 'v2': 24584}
		mlist = [(self.TestCounter, values)]
		expected = "testcounter,help=This_is_a_test_counter. v1=1i, v2=24584i 1234567890000000000\n"
		self.assertEqual(expected, influxdb_format(self.Now, mlist))


	def test_influxdb_format_named_tuple(self):
		values = {self.MetricNameTuple(method='GET', path='/asab/v1/metrics', status='200'): 0.002670550995389931, self.MetricNameTuple(method='GET', path='/asab/v1/metrics', status='404'): 0.0018205730011686683}
		mlist = [(self.TestCounter, values)]
		expected = "testcounter,help=This_is_a_test_counter.,method=GET,path=/asab/v1/metrics,status=200 testcounter=0.002670550995389931 1234567890000000000\ntestcounter,help=This_is_a_test_counter.,method=GET,path=/asab/v1/metrics,status=404 testcounter=0.0018205730011686683 1234567890000000000\n"
		self.assertEqual(expected, influxdb_format(self.Now, mlist))


	def test_influxdb_format_histogram(self):
		pass

	def test_influxdb_format_bool(self):
		# https://stackoverflow.com/questions/37888620/comparing-boolean-and-int-using-isinstance
		values_bool = {'v1': True, 'v2': False}
		mlist_bool = [(self.TestCounter, values_bool)]
		expected = 'testcounter,help=This_is_a_test_counter. v1=t, v2=f 1234567890000000000\n'
		self.assertEqual(expected, influxdb_format(self.Now, mlist_bool))

	def test_influxdb_format_str(self):
		values = {'v1': "1", 'v2': "hodně"}
		mlist = [(self.TestCounter, values)]
		expected = 'testcounter,help=This_is_a_test_counter. v1="1", v2="hodně" 1234567890000000000\n'
		self.assertEqual(expected, influxdb_format(self.Now, mlist))
