import logging
import asab

from asab.metrics.service import MetricsService
from asab.metrics import Metric, Gauge, Counter, EPSCounter, DutyCycle, AggregationCounter, Histogram, CounterWithDynamicTags, AggregationCounterWithDynamicTags, HistogramWithDynamicTags

#

L = logging.getLogger(__name__)

#


class MockApplication(object):
	def time(self):
		return 123.45


class MockMetricsService(MetricsService):
	def _add_metric(self, metric: Metric, metric_name: str, tags=None, reset=None, help=None, unit=None):
		# Add global tags
		metric.StaticTags.update(self.Tags)
		metric.App = MockApplication()

		# Add local static tags
		if tags is not None:
			metric.StaticTags.update(tags)


		metric._initialize_storage(
			self.Storage.add(metric_name, tags=metric.StaticTags.copy(), reset=reset, help=help, unit=unit)
		)

		self.Metrics.append(metric)

	def _flush_metrics(self):
		now = MockApplication().time()

		self.App.PubSub.publish("Metrics.flush!")
		for metric in self.Metrics:
			try:
				metric.flush(now)
			except Exception:
				L.exception("Exception during metric.flush()")

		return now


class Module(asab.metrics.Module):
	def __init__(self, app):
		super().__init__(app)
		self.service = MockMetricsService(app, "asab.MockMetricsService")


__all__ = (
	'MetricsService',
	'MockMetricsService',
	'Metric',
	'Gauge',
	'Counter',
	'EPSCounter',
	'DutyCycle',
	'AggregationCounter',
	'Histogram',
	'CounterWithDynamicTags',
	'AggregationCounterWithDynamicTags',
	'HistogramWithDynamicTags',
)
