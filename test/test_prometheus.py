import unittest
from asab.metrics.prometheus import metric_to_text, get_labels, validate_format


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
            "Values": {"v1": 10, "v2": 5},
        }

        expected_output = """# TYPE mycounter_v1_bytes counter
# UNIT mycounter_v1_bytes bytes
# HELP mycounter_v1_bytes The most important counter ever.
mycounter_v1_bytes_total{label="sth",other_label="sth_else"} 10
# TYPE mycounter_v2_bytes counter
# UNIT mycounter_v2_bytes bytes
# HELP mycounter_v2_bytes The most important counter ever.
mycounter_v2_bytes_total{label="sth",other_label="sth_else"} 5"""
        output = metric_to_text(input_counter, type="counter")
        self.assertEqual(expected_output, output)

        # missing labels and units
        input_counter2 = {
            "Name": "_mycounter",
            "Tags": {
                "host": "DESKTOP-6J7LEI1",
                "help": "The most important counter ever.",
            },
            "Values": {"v1": 10, "v2": 5},
        }
        expected_output2 = """# TYPE mycounter_v1 counter
# HELP mycounter_v1 The most important counter ever.
mycounter_v1_total 10
# TYPE mycounter_v2 counter
# HELP mycounter_v2 The most important counter ever.
mycounter_v2_total 5"""
        output2 = metric_to_text(input_counter2, type="counter")
        self.assertEqual(expected_output2, output2)

    def test_get_labels(self):
        input_tags = {
            "host": "DESKTOP-6J7LEI1",
            "unit": "bytes",
            "help": "The most important counter ever.",
            "label": "sth.",
            "other_label": "_sth_Else",
        }
        expected_output = '{label="sth_",other_label="sth_Else"}'
        output = get_labels(input_tags)
        self.assertEqual(expected_output, output)

        # no labels
        input_tags2 = {
            "host": "DESKTOP-6J7LEI1",
            "unit": "bytes",
            "help": "The most important counter ever.",
        }
        output2 = get_labels(input_tags2)
        self.assertIsNone(output2)

    def test_validate_format(self):
        input_name = "__My.metrics"
        expected_output = "My_metrics"
        output = validate_format(input_name)
        self.assertEqual(expected_output, output)
