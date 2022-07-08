from .baseclass import MetricsTestCase


class TestDuplicates(MetricsTestCase):

	def test_duplicates_01(self):
		Gauge1 = self.MetricsService.create_gauge("gauge1", init_values={"v1": 0})
		Gauge2 = self.MetricsService.create_gauge("gauge1", init_values={"v1": 0})
		self.assertNotEqual(Gauge1, Gauge2)
		self.assertEqual(Gauge1.Storage, Gauge2.Storage)
