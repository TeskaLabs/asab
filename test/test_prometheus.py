import unittest
from asab.metrics.openmetric import (
	metric_to_text,
	validate_format,
	validate_value,
	get_full_name,
	translate_metadata,
	get_value_labels,
)


class TestPrometheus(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super(TestPrometheus, self).__init__(*args, **kwargs)

	def test_metric_to_text(self):
		input_counter = {
			"Name": "web_requests_duration_max",
			"Tags": {
				"host": "eliska-TUXEDO-Aura-15-Gen1",
				"help": "Counts maximum request duration to asab endpoints per minute.",
			},
			"Type": "counter",
			"Values": [
				{
					"value_name": {"method": "GET", "path": "/racoon", "status": "200"},
					"value": 0.00044747701031155884,
				},
				{
					"value_name": {
						"method": "GET",
						"path": "/unicorn/5",
						"status": "404",
					},
					"value": 0.0013365640043048188
				}
			]
		}
		expected_output = """# TYPE web_requests_duration_max counter
# HELP web_requests_duration_max Counts maximum request duration to asab endpoints per minute.
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",method="GET",path="/racoon",status="200"} 0.00044747701031155884
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",method="GET",path="/unicorn/5",status="404"} 0.0013365640043048188"""
		output = metric_to_text(input_counter)
		self.assertEqual(expected_output, output)


	def test_metric_to_text_string_and_tuple(self):
		input_counter = {
			"Name": "web_requests_duration_max",
			"Tags": {
				"host": "eliska-TUXEDO-Aura-15-Gen1",
				"help": "Counts maximum request duration to asab endpoints per minute.",
			},
			"Type": "counter",
			"Values": [
				{
					"value_name": "some_name",
					"value": 0.00044747701031155884,
				},
				{
					"value_name": ("GET", "/path"),
					"value": 0.0013365640043048188
				}
			]
		}
		expected_output = """# TYPE web_requests_duration_max counter
# HELP web_requests_duration_max Counts maximum request duration to asab endpoints per minute.
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",value_name="some_name"} 0.00044747701031155884
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",label0="GET",label1="/path"} 0.0013365640043048188"""
		output = metric_to_text(input_counter)
		self.assertEqual(expected_output, output)

	def test_metric_to_text_list(self):
		input_counter = {
			"Name": "web_requests_duration_max",
			"Tags": {
				"host": "eliska-TUXEDO-Aura-15-Gen1",
				"help": "Counts maximum request duration to asab endpoints per minute.",
			},
			"Type": "counter",
			"Values": [
				{
					"value_name": "some_name",
					"value": 0.00044747701031155884,
				},
				{
					"value_name": ["GET", "/path"],
					"value": 0.0013365640043048188
				}
			]
		}
		expected_output = """# TYPE web_requests_duration_max counter
# HELP web_requests_duration_max Counts maximum request duration to asab endpoints per minute.
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",value_name="some_name"} 0.00044747701031155884
web_requests_duration_max_total{host="eliska-TUXEDO-Aura-15-Gen1",label0="GET",label1="/path"} 0.0013365640043048188"""
		output = metric_to_text(input_counter)
		self.assertEqual(expected_output, output)

	def test_get_value_labels_namedtuple(self):
		input_tags_dict = {
			"host": "eliska-TUXEDO-Aura-15-Gen1",
			"help": "Counts.",
		}
		v_name = {"method": "200", "path": "/endpoint"}
		expected_output = (
			'{host="eliska-TUXEDO-Aura-15-Gen1",help="Counts.",method="200",path="/endpoint"}'
		)
		output = get_value_labels(input_tags_dict, v_name)
		self.assertEqual(expected_output, output)

	def test_get_value_labels_tuple(self):
		input_tags_dict = {
			"host": "eliska-TUXEDO-Aura-15-Gen1",
			"help": "Counts.",
		}
		v_name = ("200", "/endpoint")
		expected_output = (
			'{host="eliska-TUXEDO-Aura-15-Gen1",help="Counts.",label0="200",label1="/endpoint"}'
		)
		output = get_value_labels(input_tags_dict, v_name)
		self.assertEqual(expected_output, output)

	def test_get_value_labels_string(self):
		input_tags_dict = {
			"host": "eliska-TUXEDO-Aura-15-Gen1",
			"help": "Counts.",
		}
		v_name = "some_name"
		expected_output = (
			'{host="eliska-TUXEDO-Aura-15-Gen1",help="Counts.",value_name="some_name"}'
		)
		output = get_value_labels(input_tags_dict, v_name)
		self.assertEqual(expected_output, output)

	def test_validate_format(self):
		input_name = "__My.metrics"
		expected_output = "My_metrics"
		output = validate_format(input_name)
		self.assertEqual(expected_output, output)

	def test_validate_value(self):
		self.assertTrue(validate_value(1))
		self.assertTrue(validate_value(1.1))
		self.assertFalse(validate_value("1"))

	def test_get_full_name(self):
		m_name, unit = "Metrics", "Unit"
		output = get_full_name(m_name, unit)
		self.assertEqual("Metrics_Unit", output)

	def test_translate_metadata(self):
		name, type, unit, help = (
			"Metrics_Value_Unit",
			"counter",
			"Unit",
			"This is help.",
		)
		output = translate_metadata(name, type, unit, help)
		expected_output = """# TYPE Metrics_Value_Unit counter
# UNIT Metrics_Value_Unit Unit
# HELP Metrics_Value_Unit This is help."""
		self.assertEqual(expected_output, output)

	def test_missing_meta(self):
		# missing labels and units
		name, type, unit, help = "Metrics_Value_Unit", "counter", None, None
		expected_output = "# TYPE Metrics_Value_Unit counter"
		output = translate_metadata(name, type, unit, help)
		self.assertEqual(expected_output, output)
