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

	def test_set_new_namedtuple(self):
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		self.TestGauge.set(value_name, 2)
		self.assertEqual(2, self.TestGauge.Values[value_name])

	def test_namedtuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.MetricNamedtuple(method="POST", path="/unicorn", status="200")
		expected = {"method": "POST", "path": "/unicorn", "status": "200"}
		self.assertEqual(expected, self.TestGauge._transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_string_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = "value_name"
		expected = "value_name"
		self.assertEqual(expected, self.TestGauge._transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_tuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.JustTuple
		expected = self.JustTuple
		self.assertEqual(expected, self.TestGauge._transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_rest_get(self):
		RestgetGauge = Gauge("testgauge", tags={'help': 'This is another Gauge.'}, init_values={"v1": 1})
		expected = {
			"Name": "testgauge",
			"Tags": {
				"help": "This is another Gauge."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			}],
			"Type": "gauge"
		}
		self.assertEqual(expected, RestgetGauge.rest_get())

	def test_rest_get_namedtuple(self):
		RestgetGauge = Gauge("testgauge", tags={'help': 'This is another Gauge.'}, init_values={"v1": 1})
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		RestgetGauge.set(value_name, 2)
		expected = {
			"Name": "testgauge",
			"Tags": {
				"help": "This is another Gauge."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			},
				{
				"value_name": {"method": "GET", "path": "/metric", "status": "200"},
				"value": 2
			}],
			"Type": "gauge"
		}
		self.assertEqual(expected, RestgetGauge.rest_get())

	def test_rest_get_tuple(self):
		RestgetGauge = Gauge("testgauge", tags={'help': 'This is another Gauge.'}, init_values={"v1": 1})
		value_name = self.JustTuple
		RestgetGauge.set(value_name, 2)
		expected = {
			"Name": "testgauge",
			"Tags": {
				"help": "This is another Gauge."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			},
				{
				"value_name": ("GET", "/metric", 200),
				"value": 2
			}],
			"Type": "gauge"
		}
		self.assertEqual(expected, RestgetGauge.rest_get())
