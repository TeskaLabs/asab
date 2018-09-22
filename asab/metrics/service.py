import configparser
import time
import logging
import platform
import asyncio
import pprint

import asab

from .metrics import Metric, Counter, Gauge

#

L = logging.getLogger(__name__)

#

class MetricsService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Loop = app.Loop
		
		self.Metrics = {}
		self.Targets = []
		self.Tags = {
			'host': platform.node(),
		}

		app.PubSub.subscribe("Application.tick/10!", self._on_flushing_event)

		for target in asab.Config.get('asab:metrics', 'target').strip().split():
			try:
				target_type =  asab.Config.get('asab:metrics:{}'.format(target), 'type')
			except configparser.NoOptionError:
				# This allows to specify the type of the target by its name
				target_type = target

			if target_type == 'influxdb':
				from .influxdb import MetricsInfluxDB
				target = MetricsInfluxDB(self, 'asab:metrics:{}'.format(target))
			else:
				raise RuntimeError("Unknown target type {}".format(target_type))

			self.Targets.append(target)


	async def finalize(self, app):
		await self._on_flushing_event("finalize!")


	async def _on_flushing_event(self, event_type):
		if len(self.Metrics) == 0: return
		now = time.time()

		mlist = []
		for metric in self.Metrics.values():
			struct_data={
				'name': metric.Name,
				'timestamp': now,
			}

			values = metric.flush()

			for fk, fv in values.items():
				struct_data['field.{}'.format(fk)] = fv

			tags = metric.Tags
			if tags is not None:
				for tk, tv in tags.items():
					struct_data['tag.{}'.format(tk)] = tv
			L.log(asab.LOG_NOTICE, "", struct_data=struct_data)
		
			mlist.append((metric, values))

		fs = []
		for target in self.Targets:
			fs.append(target.process(now, mlist))
		if len(fs) > 0:
			done, pending = await asyncio.wait(fs, loop=self.Loop, timeout=5.0, return_when=asyncio.ALL_COMPLETED)
		
		for f in pending:
			L.warning("Target task {} failed to complete".format(f))
			f.cancel()


	def add_metric(self, metric:Metric):
		self.Metrics[metric.Name] = metric


	def create_gauge(self, metric_name, tags=None, init_values=None):
		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = Gauge(metric_name, tags=t, init_values=init_values)
		self.add_metric(m)
		return m


	def create_counter(self, metric_name, tags=None, init_values=None, reset:bool=True):

		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
		else:
			t = self.Tags

		m = Counter(metric_name, tags=t, init_values=init_values, reset=reset)
		self.add_metric(m)
		return m

