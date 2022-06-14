import configparser
import logging
import asyncio
import os

import asab

from .metrics import Metric, Counter, EPSCounter, Gauge, DutyCycle, AggregationCounter, Histogram
from .storage import Storage


#

L = logging.getLogger(__name__)

#


class MetricsService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.Metrics = []
		self.Targets = []
		self.Tags = {
			"host": app.HostName,
		}
		self.Storage = Storage()

		app.PubSub.subscribe("Application.tick/60!", self._on_flushing_event)

		for target in asab.Config.get('asab:metrics', 'target').strip().split():

			try:
				target_type = asab.Config.get('asab:metrics:{}'.format(target), 'type')
			except configparser.NoOptionError:
				# This allows to specify the type of the target by its name
				target_type = target

			if target_type == 'influxdb':
				from .influxdb import InfluxDBTarget
				target = InfluxDBTarget(self, 'asab:metrics:{}'.format(target))

			elif target_type == 'http':
				from .HTTPTarget import HTTPTarget
				target = HTTPTarget(self, 'asab:metrics:{}'.format(target))

			else:
				raise RuntimeError("Unknown target type {}".format(target_type))

			self.Targets.append(target)

		# Create native metrics
		self.ProcessId = os.getpid()

		self.MemoryGauge = self.create_gauge(
			"os.stat",
			init_values=self._get_process_info(),
		)


	async def finalize(self, app):
		await self._on_flushing_event("finalize!")


	def add_target(self, target):
		self.Targets.append(target)


	def _get_process_info(self):
		memory_info = {}

		try:
			with open("/proc/{}/status".format(self.ProcessId), "r") as file:
				proc_status = file.read()

				for proc_status_line in proc_status.replace('\t', '').split('\n'):

					# Vm - virtual memory, other metrics need to be evaluated and added
					if not proc_status_line.startswith("Vm"):
						continue

					proc_status_info = proc_status_line.split(' ')

					try:
						memory_info[proc_status_info[0][:-1]] = int(proc_status_info[-2]) * 1024

					except ValueError:
						continue

		except FileNotFoundError:
			L.info("File '/proc/{}/status' was not found, skipping process metrics.".format(self.ProcessId))

		return memory_info


	async def _on_flushing_event(self, event_type):
		if len(self.Metrics) == 0:
			return

		# Update native metrics
		for key, value in self._get_process_info().items():
			self.MemoryGauge.set(key, value)

		for metric in self.Metrics:
			metric.flush()

		now = self.App.time()
		fs = []
		for target in self.Targets:
			fs.append(target.process(self.Storage.Metrics, now))

		if len(fs) > 0:
			done, pending = await asyncio.wait(fs, loop=self.App.Loop, timeout=180.0, return_when=asyncio.ALL_COMPLETED)

			for f in pending:
				L.warning("Target task {} failed to complete".format(f))
				f.cancel()


	def _add_metric(self, metric: Metric, metric_name: str, tags: dict, help=None, unit=None):
		# Add "global" tags into the metric
		if tags is None:
			tags = self.Tags.copy()
		else:
			tags = tags.copy()
			tags.update(self.Tags)

		metric._initialize_storage(
			self.Storage.add(metric_name, tags, help=help, unit=unit)
		)
		self.Metrics.append(metric)


	def create_gauge(self, metric_name, tags=None, init_values=None, help=None, unit=None):
		m = Gauge(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, help=None, unit=None):
		m = Counter(init_values=init_values, reset=reset)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_eps_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, help=None, unit=None):
		m = EPSCounter(init_values=init_values, reset=reset)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_duty_cycle(self, loop, metric_name, tags=None, init_values=None, help=None, unit=None):
		m = DutyCycle(loop, init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_agg_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, agg=max, help=None, unit=None):
		m = AggregationCounter(init_values=init_values, reset=reset, agg=agg)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_histogram(self, metric_name, buckets: list, tags=None, reset: bool = True, help=None, unit=None):
		m = Histogram(buckets=buckets, reset=reset)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m
