import configparser
import logging
import asyncio
import os

import asab

from .metrics import Metric, Counter, EPSCounter, Gauge, DutyCycle, AggregationCounter, Histogram
from .memstor import MetricsMemstorTarget


#

L = logging.getLogger('asab.metrics')

#


def metric_dimension(metric_name, tags):
	dim = metric_name
	if tags is not None:
		for k in sorted(tags.keys()):
			dim += ',{}={}'.format(k, tags[k])
	return dim


class MetricsService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.Metrics = {}  # A key is dimension (combination of metric name and tags)
		self.Targets = []
		self.Tags = {
			"host": app.HostName,
		}

		self.PrometheusTarget = None

		app.PubSub.subscribe("Application.tick/60!", self._on_flushing_event)

		for target in asab.Config.get('asab:metrics', 'target').strip().split():
			try:
				target_type = asab.Config.get('asab:metrics:{}'.format(target), 'type')
			except configparser.NoOptionError:
				# This allows to specify the type of the target by its name
				target_type = target

			if target_type == 'influxdb':
				from .influxdb import MetricsInfluxDB
				target = MetricsInfluxDB(self, 'asab:metrics:{}'.format(target))

			elif target_type == "prometheus":
				from. prometheus import PrometheusTarget
				target = PrometheusTarget(self, 'asab:metrics:prometheus')
				self.PrometheusTarget = target

			else:
				raise RuntimeError("Unknown target type {}".format(target_type))

			self.Targets.append(target)

		# Memory storage target
		self.MemstorTarget = MetricsMemstorTarget(self, 'asab:metrics:memory')
		self.Targets.append(self.MemstorTarget)

		# Create native metrics
		self.ProcessId = os.getpid()

		self.MemoryGauge = self.create_gauge(
			"asab.memory",
			init_values=self._get_process_memory_info(),
			tags={
				"unit": "bytes",
				"help": "Memory consumed by the process.",
			},
		)


	async def finalize(self, app):
		await self._on_flushing_event("finalize!")


	def add_target(self, target):
		self.Targets.append(target)


	def _get_process_memory_info(self):
		memory_info = {}

		try:
			with open("/proc/{}/status".format(self.ProcessId), "r") as file:
				proc_status = file.read()

				for proc_status_line in proc_status.replace('\t', '').split('\n'):

					# Vm - virtual memory
					if not proc_status_line.startswith("Vm"):
						continue

					proc_status_info = proc_status_line.split(' ')
					memory_info[proc_status_info[0][:-1]] = int(proc_status_info[-2]) * 1024

		except FileNotFoundError:
			L.info("File '/proc/{}/status' was not found, skipping memory metrics.".format(self.ProcessId))

		return memory_info


	async def _on_flushing_event(self, event_type):
		if len(self.Metrics) == 0:
			return
		now = self.App.time()

		# Update native metrics
		for key, value in self._get_process_memory_info().items():
			self.MemoryGauge.set(key, value)

		mlist = []

		for metric in self.Metrics.values():
			struct_data = {
				'name': metric.Name,
				'timestamp': now,
			}

			values = metric.flush()

			# Skip empty values
			if len(values) == 0:
				continue

			for fk, fv in values.items():
				struct_data['field.{}'.format(fk)] = fv

			tags = metric.Tags
			if tags is not None:
				for tk, tv in tags.items():
					struct_data['tag.{}'.format(tk)] = tv

			# Log metrics into the logger
			# To enable seing this in normal ASAB mode, use following configuration:
			#
			# [logging]
			# levels=
			#   asab.metrics INFO
			L.info("", struct_data=struct_data)

			mlist.append((metric, values))

			self.App.PubSub.publish(
				"Application.Metrics.Flush!",
				metric, values,
				asynchronously=False
			)

		fs = []
		for target in self.Targets:
			fs.append(target.process(now, mlist))
		if len(fs) > 0:
			done, pending = await asyncio.wait(fs, loop=self.App.Loop, timeout=180.0, return_when=asyncio.ALL_COMPLETED)

			for f in pending:
				L.warning("Target task {} failed to complete".format(f))
				f.cancel()


	def _add_metric(self, dimension, metric: Metric):
		dimension = metric_dimension(metric.Name, metric.Tags)
		self.Metrics[dimension] = metric


	def create_gauge(self, metric_name, tags=None, init_values=None):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = Gauge(metric_name, tags=t, init_values=init_values)
		self._add_metric(dimension, m)
		return m


	def create_counter(self, metric_name, tags=None, init_values=None, reset: bool = True):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = Counter(metric_name, tags=t, init_values=init_values, reset=reset)
		self._add_metric(dimension, m)
		return m


	def create_eps_counter(self, metric_name, tags=None, init_values=None, reset: bool = True):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = EPSCounter(metric_name, tags=t, init_values=init_values, reset=reset)
		self._add_metric(dimension, m)
		return m


	def create_duty_cycle(self, loop, metric_name, tags=None, init_values=None):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = DutyCycle(loop, metric_name, tags=t, init_values=init_values)
		self._add_metric(dimension, m)
		return m

	def create_agg_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, agg=max):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = AggregationCounter(metric_name, tags=t, init_values=init_values, reset=reset, agg=agg)
		self._add_metric(dimension, m)
		return m

	def create_histogram(self, metric_name, buckets: list, tags=None, reset: bool = True):
		dimension = metric_dimension(metric_name, tags)
		if dimension in self.Metrics:
			raise RuntimeError("Metric '{}' already present".format(dimension))

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = Histogram(metric_name, buckets=buckets, tags=t, reset=reset)
		self._add_metric(dimension, m)
		return m
