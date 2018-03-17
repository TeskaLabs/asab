import logging
import asyncio
import argparse
import itertools
import os
import signal
import platform

from .config import Config
from .abc.singleton import Singleton
from .log import _setup_logging, _loop_exception_handler

from .metrics import Metrics

# Importing the Win API library
if platform.system() == "Windows":
	try:
		import win32api
	except ModuleNotFoundError:
		win32api = None
else:
	win32api = None

#

L = logging.getLogger(__name__)

#

class Application(metaclass=Singleton):


	Description = ""


	def __init__(self):

		# Parse command line
		self.parse_args()

		# Load configuration
		Config._load()

		# Setup logging
		_setup_logging()

		# Configure event loop
		self.Loop = asyncio.get_event_loop()
		self.Loop.set_exception_handler(_loop_exception_handler)
		if Config["general"]["verbose"] == "True":
			self.Loop.set_debug(True)

		
		try:
			# Signals are not available on Windows
			self.Loop.add_signal_handler(signal.SIGINT, self.stop)
		except NotImplementedError:
			# Checking if the program runs on Windows
			if any(platform.win32_ver()):
				if win32api is not None:
					callBack = self.stop
					# Adding a handler to listen to the interrupt event
					def handler(type):
						callBack()
						return True
					win32api.SetConsoleCtrlHandler(handler, True)

		try:
			self.Loop.add_signal_handler(signal.SIGTERM, self.stop)
		except NotImplementedError:
			pass

		self._stop_event = asyncio.Event(loop = self.Loop)
		self._stop_event.clear()
		self._stop_counter = 0

		from .pubsub import PubSub
		self.PubSub = PubSub(self)
		self.Metrics = Metrics(self)

		self.Modules = []
		self.Services = {}

		# Comence init-time governor
		L.info("Initializing ...")
		finished_tasks, pending_tasks = self.Loop.run_until_complete(asyncio.wait(
			[
				self.initialize(),
				self._init_time_governor(asyncio.Future()),
			],
			return_when = asyncio.FIRST_EXCEPTION
		))
		for task in finished_tasks:
			# This one also raises exceptions from futures, which is perfectly ok
			task.result()
		if len(pending_tasks) > 0:
			raise RuntimeError("Failed to fully initialize. Here are pending tasks: {}".format(pending_tasks))


	def parse_args(self):
		'''
		This method can be overriden to adjust argparse configuration 
		'''

		parser = argparse.ArgumentParser(
			formatter_class=argparse.RawDescriptionHelpFormatter,
			description=self.Description,
		)
		parser.add_argument('-c', '--config', help='Path to configuration file (default: %(default)s)', default=Config._default_values['general']['config_file'])
		parser.add_argument('-v', '--verbose', action='store_true', help='Print more information (enable debug output)')

		args = parser.parse_args()
		if args.config is not None:
			Config._default_values['general']['config_file'] = args.config

		if args.verbose:
			Config._default_values['general']['verbose'] = True


	def run(self):
		# Comence run-time and application main() function
		L.info("Running ...")
		self._stop_event.clear()
		finished_tasks, pending_tasks = self.Loop.run_until_complete(asyncio.wait(
			[
				self.main(),
				self._run_time_governor(asyncio.Future()),
			],
			return_when = asyncio.FIRST_EXCEPTION
		))
		for task in finished_tasks:
			try:
				task.result()
			except Exception:
				L.exception("Exception in {}".format(task))

		#TODO: Process pending_tasks tasks from above

		# Comence exit-time
		L.info("Exiting ...")
		finished_tasks, pending_tasks = self.Loop.run_until_complete(asyncio.wait(
			[
				self.finalize(),
				self._exit_time_governor(asyncio.Future()),
			],
			return_when = asyncio.FIRST_EXCEPTION
		))
		for task in finished_tasks:
			try:
				task.result()
			except Exception:
				L.exception("Exception in {}".format(task))

		#TODO: Process pending_tasks tasks from above


		self.Loop.close()

		try:
			# EX_OK code is not available on Windows
			return os.EX_OK
		except AttributeError:
			return 0


	def stop(self):
		self._stop_event.set()
		self._stop_counter += 1
		if self._stop_counter >= 3:
			L.fatal("Emergency exit")
			try:
				# EX_SOFTWARE code is not available on Windows
				return os._exit(os.EX_SOFTWARE)
			except AttributeError:
				return os._exit(0)


	# Modules

	def add_module(self, module_class):
		""" Load a new module. """

		module = module_class(self)
		self.Modules.append(module)
	
		asyncio.ensure_future(module.initialize(self), loop=self.Loop)

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
			raise RuntimeError("Service {} already registered".format(service_name))

		self.Services[service_name] = service

		asyncio.ensure_future(service.initialize(self), loop=self.Loop)


	# Lifecycle callback

	async def initialize(self):
		pass

	async def main(self):
		pass

	async def finalize(self):
		pass

	# Governors

	async def _init_time_governor(self, future):
		self.PubSub.publish("Application.init!")
		future.set_result("initialize")


	async def _run_time_governor(self, future):
		timeout = Config.getint('general', 'tick_period')
		try:
			self.PubSub.publish("Application.run!")

			# Wait for stop event & tick in meanwhile
			for cycle_no in itertools.count(1):
				try:
					await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
					break
				except asyncio.TimeoutError:
					self.Metrics.add("Application.tick", 1)
					self.PubSub.publish("Application.tick!")
					if (cycle_no % 10) == 0: self.PubSub.publish("Application.tick/10!")
					if (cycle_no % 60) == 0: self.PubSub.publish("Application.tick/60!")
					if (cycle_no % 300) == 0: self.PubSub.publish("Application.tick/300!")
					if (cycle_no % 600) == 0: self.PubSub.publish("Application.tick/600!")
					if (cycle_no % 1800) == 0: self.PubSub.publish("Application.tick/1800!")
					if (cycle_no % 3600) == 0: self.PubSub.publish("Application.tick/3600!")
					if (cycle_no % 43200) == 0: self.PubSub.publish("Application.tick/43200!")
					if (cycle_no % 86400) == 0: self.PubSub.publish("Application.tick/86400!")
					continue

		finally:
			future.set_result("run")


	async def _exit_time_governor(self, future):
		self.PubSub.publish("Application.exit!")

		# Finalize services
		futures = []
		for service in self.Services.values():
			nf = asyncio.ensure_future(service.finalize(self), loop=self.Loop)
			futures.append(nf)
		if len(futures) > 0:
			await asyncio.wait(futures, return_when=asyncio.ALL_COMPLETED)
			# TODO: Handle expections (if needed) - probably only print them

		# Finalize modules
		futures = []
		for module in self.Modules:
			nf = asyncio.ensure_future(module.finalize(self), loop=self.Loop)
			futures.append(nf)
		if len(futures) > 0:
			await asyncio.wait(futures, return_when=asyncio.ALL_COMPLETED)
			# TODO: Handle expections (if needed) - probably only print them

		future.set_result("exit")
