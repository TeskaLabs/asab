import asyncio
import logging

from . import metrics

L = logging.getLogger(__name__)


class EventLoopProfiler(object):

	def __init__(self, loop=None, start=True, interval=10):
		self._interval = interval
		self._stopped = False
		self.ProfilingCounter = metrics.ProfilingCounter(
			"asab.profiling_counter",
			tags={'profiler': self.__class__.__name__},
			init_values={
				'event_loop.delay': .0,
			}
		)
		self._loop = loop or asyncio.get_event_loop()
		if start:
			self.start()

	def run(self):
		self._loop.call_later(self._interval, self._handler, self._loop.time())

	def _handler(self, start_time):
		latency = (self._loop.time() - start_time) - self._interval
		self.ProfilingCounter.add("event_loop.delay", latency)
		if not self.is_stopped():
			self.run()

	def is_stopped(self):
		return self._stopped

	def start(self):
		self._stopped = False
		self.run()

	def stop(self):
		self._stopped = True
