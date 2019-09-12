#!/usr/bin/env python3
import logging

import requests

import asab

L = logging.getLogger(__name__)


class ProfilingApplication(asab.Application):

	async def initialize(self):
		# The timer will trigger a message publishing at every second
		self.Timer = asab.Timer(self, self.on_tick, autorestart=True)
		self.Timer.start(5)

	async def on_tick(self):
		L.info("Sending request with 2 sec delay")
		requests.get(f"https://httpbin.org/delay/2")
		L.info("Got response")
		L.warning(self.Profiler.ProfilingCounter.rest_get())


if __name__ == '__main__':
	args = {'--profile': True}
	app = ProfilingApplication(args=args)
	app.run()
