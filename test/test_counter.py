import unittest
import collections
from asab.metrics.metrics import Counter, _transform_namedtuple_valuename_to_labelset_dict


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

	def test_add_new_namedtuple(self):
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		self.TestCounter.add(value_name, 2, 0)
		self.assertEqual(2, self.TestCounter.Values[value_name])

	def test_namedtuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.MetricNamedtuple(method="POST", path="/unicorn", status="200")
		expected = {"method": "POST", "path": "/unicorn", "status": "200"}
		self.assertEqual(expected, _transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_string_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = "value_name"
		expected = "value_name"
		self.assertEqual(expected, _transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_tuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.JustTuple
		expected = self.JustTuple
		self.assertEqual(expected, _transform_namedtuple_valuename_to_labelset_dict(value_name))

	def test_rest_get(self):
		RestgetCounter = Counter("testcounter", tags={'help': 'This is another counter.'}, init_values={"v1": 1})
		expected = {
			"Name": "testcounter",
			"Tags": {
				"help": "This is another counter."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			}],
			"Type": "counter"
		}
		self.assertEqual(expected, RestgetCounter.rest_get())

	def test_rest_get_namedtuple(self):
		RestgetCounter = Counter("testcounter", tags={'help': 'This is another counter.'}, init_values={"v1": 1})
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		RestgetCounter.add(value_name, 2, 0)
		expected = {
			"Name": "testcounter",
			"Tags": {
				"help": "This is another counter."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			},
				{
				"value_name": {"method": "GET", "path": "/metric", "status": "200"},
				"value": 2
			}],
			"Type": "counter"
		}
		self.assertEqual(expected, RestgetCounter.rest_get())

	def test_rest_get_tuple(self):
		RestgetCounter = Counter("testcounter", tags={'help': 'This is another counter.'}, init_values={"v1": 1})
		value_name = self.JustTuple
		RestgetCounter.add(value_name, 2, 0)
		expected = {
			"Name": "testcounter",
			"Tags": {
				"help": "This is another counter."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			},
				{
				"value_name": ("GET", "/metric", 200),
				"value": 2
			}],
			"Type": "counter"
		}
		self.assertEqual(expected, RestgetCounter.rest_get())

	def test_last_values(self):
		RestgetCounter = Counter("testcounter", tags={'help': 'This is another counter.'}, init_values={"v1": 1})
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		RestgetCounter.add(value_name, 2, 0)
		RestgetCounter.flush()
		expected = {
			"Name": "testcounter",
			"Tags": {
				"help": "This is another counter."
			},
			"Values": [{
				"value_name": "v1",
				"value": 1
			},
				{
				"value_name": {"method": "GET", "path": "/metric", "status": "200"},
				"value": 2
			}],
			"Type": "counter"
		}
		self.assertEqual(expected, RestgetCounter.LastRecord)
