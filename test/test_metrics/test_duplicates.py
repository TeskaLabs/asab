from .baseclass import MetricsTestCase


class TestDuplicates(MetricsTestCase):

	def test_duplicates_01(self):
		try:
			Gauge1 = self.MetricsService.create_gauge("gauge1", init_values={"v1": 0})
		finally:
			pass
		Gauge2 = self.MetricsService.create_gauge("gauge1", init_values={"v1": 0})
