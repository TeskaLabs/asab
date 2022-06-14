import unittest
import collections
from asab.metrics.metrics import Gauge


class TestGauge(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestGauge, self).__init__(*args, **kwargs)
		self.TestGauge = Gauge("testgauge", tags={'help': 'This is a test Gauge.'}, init_values={"v1": 1})
		self.MetricNamedtuple = collections.namedtuple("labels", ["method", "path", "status"])
		self.JustTuple = ("GET", "/metric", 200)

	def test_set_existing_value(self):
		self.TestGauge.set("v1", 2)
		self.assertEqual(2, self.TestGauge.Values["v1"])

	def test_set_new_value(self):
		self.TestGauge.set("v2", 2)
		self.assertEqual(2, self.TestGauge.Values["v2"])

	def test_rest_get(self):
		RestgetGauge = Gauge("testgauge", tags={'help': 'This is another Gauge.'}, init_values={"v1": 1})
		expected = {
			"Name": "testgauge",
			"Tags": {
				"help": "This is another Gauge."
			},
			"Values": {"v1": 1},
			"Type": "Gauge"
		}
		self.assertEqual(expected, RestgetGauge.rest_get())
