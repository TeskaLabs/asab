import unittest
import collections
from asab.metrics.metrics import Histogram


class TestHistogram(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestHistogram, self).__init__(*args, **kwargs)
		self.TestHistorgram = Histogram(
			"testhistogram", [1, 10, 100], tags={"help": "This is a test Histogram."}
		)
		self.MetricNamedtuple = collections.namedtuple(
			"labels", ["method", "path", "status"]
		)
		self.JustTuple = ("GET", "/metric", 200)

	def test_set_existing_value(self):
		self.TestHistorgram.set("v1", 2)
		self.assertEqual(1, self.TestHistorgram.Buckets[10]["v1"])
		self.assertEqual(2, self.TestHistorgram.Sum)
