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

	def test_set_new_namedtuple(self):
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		self.TestHistorgram.set(value_name, 2)
		self.assertEqual(1, self.TestHistorgram.Buckets[10][value_name])

	def test_namedtuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.MetricNamedtuple(method="POST", path="/unicorn", status="200")
		upperbound = 10
		expected = {"method": "POST", "path": "/unicorn", "status": "200", "le": "10"}
		self.assertEqual(
			expected,
			self.TestHistorgram._transform_namedtuple_valuename_to_labelset_dict(
				value_name, upperbound
			),
		)

	def test_string_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = "my_nice_field"
		upperbound = 10
		expected = {"value_name": "my_nice_field", "le": "10"}
		self.assertEqual(
			expected,
			self.TestHistorgram._transform_namedtuple_valuename_to_labelset_dict(
				value_name, upperbound
			),
		)

	def test_tuple_in_transform_namedtuple_valuename_to_labelset_dict(self):
		value_name = self.JustTuple
		upperbound = 10
		expected = {"value_name": self.JustTuple, "le": "10"}
		self.assertEqual(
			expected,
			self.TestHistorgram._transform_namedtuple_valuename_to_labelset_dict(
				value_name, upperbound
			),
		)

	def test_rest_get(self):
		RestgetHistogram = Histogram(
			"testhistogram", [1, 10, 100], tags={"help": "This is another Histogram."}
		)
		expected = {
			"Name": "testhistogram",
			"Tags": {"help": "This is another Histogram."},
			"Values": [
				{"value_name": "Sum", "value": 0.0},
				{"value_name": "Count", "value": 0},
			],
			"Type": "histogram",
		}
		self.assertEqual(expected, RestgetHistogram.rest_get())

	def test_rest_get_namedtuple(self):
		RestgetHistogram = Histogram(
			"testhistogram", [1, 10, 100], tags={"help": "This is another Histogram."}
		)
		value_name = self.MetricNamedtuple(method="GET", path="/metric", status="200")
		RestgetHistogram.set(value_name, 2)
		expected = {
			"Name": "testhistogram",
			"Tags": {"help": "This is another Histogram."},
			"Values": [
				{
					"value_name": {"method": "GET", "path": "/metric", "status": "200", "le": "10.0"},
					"value": 1
				},
				{
					"value_name": {"method": "GET", "path": "/metric", "status": "200", "le": "100.0"},
					"value": 1
				},
				{
					"value_name": {"method": "GET", "path": "/metric", "status": "200", "le": "inf"},
					"value": 1
				},
				{"value_name": "Sum", "value": 2.0},
				{"value_name": "Count", "value": 1},
			],
			"Type": "histogram",
		}
		self.assertEqual(expected, RestgetHistogram.rest_get())

	def test_rest_get_tuple(self):
		RestgetHistogram = Histogram(
			"testhistogram", [1, 10, 100], tags={"help": "This is another Histogram."}
		)
		value_name = self.JustTuple
		RestgetHistogram.set(value_name, 2)
		expected = {
			"Name": "testhistogram",
			"Tags": {"help": "This is another Histogram."},
			"Values": [
				{
					"value_name": {"value_name": ("GET", "/metric", 200), "le": "10.0"},
					"value": 1
				},
				{
					"value_name": {"value_name": ("GET", "/metric", 200), "le": "100.0"},
					"value": 1
				},
				{
					"value_name": {"value_name": ("GET", "/metric", 200), "le": "inf"},
					"value": 1
				},
				{"value_name": "Sum", "value": 2.0},
				{"value_name": "Count", "value": 1},
			],
			"Type": "histogram",
		}
		self.assertEqual(expected, RestgetHistogram.rest_get())
