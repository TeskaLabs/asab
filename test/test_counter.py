import unittest
import collections
from asab.metrics.metrics import Counter


class TestCounter(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestCounter, self).__init__(*args, **kwargs)
		self.TestCounter = Counter("testgauge", tags={'help': 'This is a test Gauge.'}, init_values={"v1": 1})
		self.MetricNamedtuple = collections.namedtuple("labels", ["method", "path", "status"])
		self.JustTuple = ("GET", "/metric", 200)

	def test_add_to_existing_value(self):
		self.TestCounter.add("v1", 2)
		self.assertEqual(3, self.TestCounter.Values["v1"])

	def test_set_new_value(self):
		self.TestCounter.add("v2", 2, 0)
		self.assertEqual(2, self.TestCounter.Values["v2"])

	def test_rest_get(self):
		RestgetCounter = Counter("testcounter", tags={'help': 'This is another counter.'}, init_values={"v1": 1})
		expected = {
			"Name": "testcounter",
			"Tags": {
				"help": "This is another counter."
			},
			"Values": {"v1": 1},
			"Type": "Counter"
		}
		self.assertEqual(expected, RestgetCounter.rest_get())
