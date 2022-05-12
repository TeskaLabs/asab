import logging
import asab

from .service import MetricsService
from .metrics import Metric, Gauge, Counter, EPSCounter, DutyCycle, AggregationCounter
from .influxdb import MetricsInfluxDB
from .http_target import HTTPTarget

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:metrics': {
			'target': '',  # Can be multiline
		}
	}
)


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
	'MetricsInfluxDB',
	'HTTPTarget',
)
