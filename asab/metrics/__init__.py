import logging
import asab

from .service import MetricsService
from .metrics import Metric, Gauge, Counter, EPSCounter, DutyCycle, AggregationCounter, Histogram, CounterWithDynamicTags, AggregationCounterWithDynamicTags, HistogramWithDynamicTags

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = MetricsService(app, "asab.MetricsService")


__all__ = (
	'MetricsService',
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
