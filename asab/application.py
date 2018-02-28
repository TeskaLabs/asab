import logging
import asyncio
import os
import signal

from .config import Config
from .abc.singleton import Singleton
from .pubsub import PubSub
from .metrics import Metrics

#

L = logging.getLogger(__file__)

#


class Application(metaclass=Singleton):


	def __init__(self):

		# Load configuration
		self.Config = Config
		self.Config.load()

		# Configure event loop
		self.Loop = asyncio.get_event_loop()
		self.Loop.add_signal_handler(signal.SIGINT, self.stop)
		self.Loop.add_signal_handler(signal.SIGTERM, self.stop)
		self.StopEvent = asyncio.Event(loop = self.Loop)
		self.StopEvent.clear()

		self.PubSub = PubSub(self)
		self.Metrics = Metrics(self)

		self.Modules = []
		self.Services = {}

		# Launch init time governor
		L.info("Initializing ...")
		future = asyncio.Future()
		asyncio.ensure_future(self.init_time_governor(future))
		self.Loop.run_until_complete(future)


	def run(self):
		# Launch run time governor
		L.info("Running ...")
		self.StopEvent.clear()
		future = asyncio.Future()
		asyncio.ensure_future(self.run_time_governor(future))
		self.Loop.run_until_complete(future)

		# Launch exit time governor
		L.info("Exiting ...")
		future = asyncio.Future()
		asyncio.ensure_future(self.exit_time_governor(future))
		self.Loop.run_until_complete(future)

		self.Loop.close()

		return os.EX_OK


	def stop(self):
		self.StopEvent.set()

	# Modules

	def add_module(self, module_class):
		""" Load a new module. """

		module = module_class(self)
		self.Modules.append(module)

	# Services

	def get_service(self, service_name):
		""" Get a new service by its name. """

		try:
			return self.Services[service_name]
		except KeyError:
			pass

		L.error("Cannot find service '{}' - not registered?".format(service_name))
		raise KeyError("Cannot find service '{}'".format(service_name))

	def register_service(self, service_name, service):
		""" Register a new service using its name. """

		if service_name in self.Services:
			L.error("Service '{}' already registered (existing:{} new:{})"
					.format(service_name, self.Services[service_name], service))
			raise KeyError("Service {} already registered".format(service_name))

		self.Services[service_name] = service
		return True

	# Governors

	async def init_time_governor(self, future):
		self.PubSub.publish("init")
		future.set_result("init")


	async def run_time_governor(self, future):
		timeout = self.Config.getint('general', 'tick_period')
		try:
			self.PubSub.publish("run")
			while True:
				try:
					await asyncio.wait_for(self.StopEvent.wait(), timeout=timeout)
					break
				except asyncio.TimeoutError:
					self.PubSub.publish("tick")
					continue

		finally:
			future.set_result("run")


	async def exit_time_governor(self, future):
		print("Exiting ...")
		self.PubSub.publish("exit")
		future.set_result("exit")
