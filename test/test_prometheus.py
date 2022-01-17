import unittest
from asab.metrics.prometheus import counter_to_om, get_labels, validate_format


class TestPrometheus(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPrometheus, self).__init__(*args, **kwargs)

    def test_counter_to_om(self):
        input_counter = {'Name': 'mycounter', 'Tags': {'host': 'DESKTOP-6J7LEI1', 'unit': 'bytes', 'help': 'The most important counter ever.', 'label': 'sth', 'other_label': 'sth_else'}, 'Values': {'v1': 10, 'v2': 5}}

        expected_output = '# TYPE mycounter_v1_bytes counter\n# UNIT mycounter_v1_bytes bytes\n# HELP mycounter_v1_bytes The most important counter ever.\nmycounter_v1_bytes_total{label="sth",other_label="sth_else"} 10\n# TYPE mycounter_v2_bytes counter\n# UNIT mycounter_v2_bytes bytes\n# HELP mycounter_v2_bytes The most important counter ever.\nmycounter_v2_bytes_total{label="sth",other_label="sth_else"} 5'
        output = counter_to_om(input_counter)
        self.assertEqual(expected_output, output)

        # missing labels and units
        input_counter2 = {'Name': 'mycounter', 'Tags': {'host': 'DESKTOP-6J7LEI1', 'help': 'The most important counter ever.'}, 'Values': {'v1': 10, 'v2': 5}}
        expected_output2 = '# TYPE mycounter_v1 counter\n# HELP mycounter_v1 The most important counter ever.\nmycounter_v1_total 10\n# TYPE mycounter_v2 counter\n# HELP mycounter_v2 The most important counter ever.\nmycounter_v2_total 5'
        output2 = counter_to_om(input_counter2)
        self.assertEqual(expected_output2, output2)

    def test_get_labels(self):
        input_tags = {'host': 'DESKTOP-6J7LEI1', 'unit': 'bytes', 'help': 'The most important counter ever.', 'label': 'sth', 'other_label': 'sth_else'}
        expected_output = '{label="sth",other_label="sth_else"}'
        output = get_labels(input_tags)
        self.assertEqual(expected_output, output)

        # no labels
        input_tags2 = {'host': 'DESKTOP-6J7LEI1', 'unit': 'bytes', 'help': 'The most important counter ever.'}
        output2 = get_labels(input_tags2)
        self.assertIsNone(output2)

    def test_validate_format(self):
        input_name = "Moje.metrička"
        expected_output = "moje_metri_ka"
        output = validate_format(input_name)
        self.assertEqual(expected_output, output)
