import unittest
import json
from asab.metrics.prometheus import counter_to_om

class TestPrometheus(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPrometheus, self).__init__(*args, **kwargs)

    def test_counter_to_om(self):
        input_counter = {'Name': 'mycounter', 'Tags': {'host': 'DESKTOP-6J7LEI1', 'unit': 'bytes', 'help': 'The most important counter ever.', 'label':'sth', 'other_label':'sth_else'}, 'Values': {'v1': 10, 'v2': 5}}

        expected_output ='# TYPE mycounter_v1_bytes counter\n# UNIT mycounter_v1_bytes bytes\n# HELP mycounter_v1_bytes The most important counter ever.\nmycounter_v1_bytes_total{label="sth",other_label="sth_else"} 10\n# TYPE mycounter_v2_bytes counter\n# UNIT mycounter_v2_bytes bytes\n# HELP mycounter_v2_bytes The most important counter ever.\nmycounter_v2_bytes_total{label="sth",other_label="sth_else"} 5'
        output = counter_to_om(input_counter)
        self.assertEqual(expected_output, output)
