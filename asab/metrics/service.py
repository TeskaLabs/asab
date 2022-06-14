import configparser
import logging
import asyncio

from ..config import Config
from ..abc import Service
from .metrics import Metric, Counter, EPSCounter, Gauge, DutyCycle, AggregationCounter, Histogram
from .storage import Storage


#

L = logging.getLogger(__name__)

#


class MetricsService(Service):

	def __init__(self, app, service_name):

		super().__init__(app, service_name)

		self.Metrics = []
		self.Targets = []
		self.Tags = {
			"host": app.HostName,
		}
		self.Storage = Storage()

		app.PubSub.subscribe("Application.tick!", self._on_flushing_event)

		if Config.has_option('asab:metrics', 'target'):
			for target in Config.get('asab:metrics', 'target').split():
				target = target.strip()
				try:
					target_type = Config.get('asab:metrics:{}'.format(target), 'type')
				except configparser.NoOptionError:
					# This allows to specify the type of the target by its name
					target_type = target

				if target_type == 'influxdb':
					from .influxdb import InfluxDBTarget
					target = InfluxDBTarget(self, 'asab:metrics:{}'.format(target))

				elif target_type == 'http':
					from .http import HTTPTarget
					target = HTTPTarget(self, 'asab:metrics:{}'.format(target))

				else:
					raise RuntimeError("Unknown target type {}".format(target_type))

				self.Targets.append(target)

		if Config.getboolean('asab:metrics', 'native_metrics'):
			from .native import NativeMetrics
			self._native_svc = NativeMetrics(self.App, self)


	async def finalize(self, app):
		await self._on_flushing_event("finalize!")


	def _flush_metrics(self):
		self.App.PubSub.publish("Metrics.flush!")
		for metric in self.Metrics:
			try:
				metric.flush()
			except Exception:
				L.exception("Exception during metric.flush()")


	async def _on_flushing_event(self, event_type):
		if len(self.Metrics) == 0:
			return

		self._flush_metrics()

		now = self.App.time()
		pending = set()
		for target in self.Targets:
			pending.add(
				target.process(self.Storage.Metrics, now)
			)

		while len(pending) > 0:
			done, pending = await asyncio.wait(pending, loop=self.App.Loop, timeout=180.0, return_when=asyncio.ALL_COMPLETED)


	def _add_metric(self, metric: Metric, metric_name: str, tags: dict, reset=None, help=None, unit=None):
		# Add "global" tags into the metric
		if tags is None:
			tags = self.Tags.copy()
		else:
			tags = tags.copy()
			tags.update(self.Tags)

		metric._initialize_storage(
			self.Storage.add(metric_name, tags, reset=reset, help=help, unit=unit)
		)
		self.Metrics.append(metric)


	def create_gauge(self, metric_name, tags=None, init_values=None, help=None, unit=None):
		m = Gauge(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, help=None, unit=None):
		m = Counter(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_eps_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, help=None, unit=None):
		m = EPSCounter(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_duty_cycle(self, loop, metric_name, tags=None, init_values=None, help=None, unit=None):
		m = DutyCycle(loop, init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_agg_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, agg=max, help=None, unit=None):
		m = AggregationCounter(init_values=init_values, agg=agg)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_histogram(self, metric_name, buckets: list, tags=None, reset: bool = True, help=None, unit=None):
		m = Histogram(buckets=buckets)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m
