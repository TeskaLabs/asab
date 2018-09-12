import configparser
import time
import logging
import platform
import asyncio

import asab

#

L = logging.getLogger(__name__)

#

class MetricsService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Loop = app.Loop
		
		self.Cache = []
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
		if len(self.Cache) == 0: return
		cache = self.Cache
		self.Cache = []

		for line in cache:
			struct_data={
				'name': line['name'],
				'timestamp': line['timestamp'],
			}
			for fk, fv in line['fields'].items():
				struct_data['field.{}'.format(fk)] = fv
			tags = line.get('tags')
			if tags is not None:
				for tk, tv in tags.items():
					struct_data['tag.{}'.format(tk)] = tv
			L.log(asab.LOG_NOTICE, "", struct_data=struct_data)
		
		fs = []
		for target in self.Targets:
			fs.append(target.process(cache))
		if len(fs) > 0:
			done, pending = await asyncio.wait(fs, loop=self.Loop, timeout=5.0, return_when=asyncio.ALL_COMPLETED)
		
			for f in pending:
				L.warning("Target task {} failed to complete".format(f))
				f.cancel()


	def add(self, metric_name, fields, tags=None, timestamp=None):
		if isinstance(fields, int) or isinstance(fields, float) or  isinstance(fields, str):
			fields = {'value': fields}
		
		if timestamp is None:
			timestamp = time.time()

		e = {
			'name': metric_name,
			'fields': fields,
			'timestamp': timestamp,
		}
		if tags is not None:
			t = self.Tags.copy()
			t.update(tags)
			e['tags'] = t
		else:
			e['tags'] = self.Tags

		self.Cache.append(e)
