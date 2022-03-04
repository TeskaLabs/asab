import unittest
from asab.metrics.openmetric import (
    metric_to_text,
    validate_format,
    validate_value,
    get_full_name,
    translate_metadata,
    get_tags_labels,
    get_value_labels,
)


class TestPrometheus(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPrometheus, self).__init__(*args, **kwargs)

    def test_metric_to_text(self):
        input_counter = {
            "Name": "mycounter",
            "Tags": {
                "host": "DESKTOP-6J7LEI1",
                "unit": "bytes",
                "help": "The most important counter ever.",
                "label": "sth",
                "other_label": "sth_else",
            },
            "Values": {"v1": 15, "v2": 50},
        }
        expected_output = """# TYPE mycounter_bytes gauge
# UNIT mycounter_bytes bytes
# HELP mycounter_bytes The most important counter ever.
mycounter_bytes{label="sth",other_label="sth_else",value_name="v1"} 10
mycounter_bytes{label="sth",other_label="sth_else",value_name="v2"} 5"""
        output = metric_to_text(input_counter, "gauge", {"v1": 10, "v2": 5})
        self.assertEqual(expected_output, output)


    def test_get_tags_labels(self):
        input_tags = {
            "host": "DESKTOP-6J7LEI1",
            "unit": "bytes",
            "help": "The most important counter ever.",
            "label": "sth.",
            "other_label": "_sth_Else",
        }
        expected_output = {"label": "sth.", "other_label": "_sth_Else"}
        output = get_tags_labels(input_tags)
        self.assertEqual(expected_output, output)

    def test_get_value_labels(self):
        input_tags_dict = {"label": "sth_", "other_label": "sth_Else"}
        v_name = "labels(method='200', path='/endpoint')"
        expected_output = '{label="sth_",other_label="sth_Else",method="200",path="/endpoint"}'
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
