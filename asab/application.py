import logging
import asyncio
import argparse
import itertools
import os
import sys
import time
import signal
import platform
import random

try:
	import daemon
	import daemon.pidfile
except ImportError:
	daemon = None

from .config import Config
from .abc.singleton import Singleton
from .log import Logging, _loop_exception_handler

# Importing the Win API library
if platform.system() == "Windows":
	try:
		import win32api
	except ModuleNotFoundError:
		win32api = None
else:
	win32api = None


L = logging.getLogger(__name__)


class Application(metaclass=Singleton):

	Description = "This app is based on ASAB."

	def __init__(self):

		try:
			# EX_OK code is not available on Windows
			self.ExitCode = os.EX_OK
		except AttributeError:
			self.ExitCode = 0

		# Parse command line
		args = self.parse_arguments()

		# Load configuration
		Config._load()

		if hasattr(args, "daemonize") and args.daemonize:
			self.daemonize()

		elif hasattr(args, "kill") and args.kill:
			self.daemon_kill()

		# Seed the random generator
		random.seed()

		# Obtain the event loop
		self.Loop = asyncio.get_event_loop()

		# Setup logging
		self.Logging = Logging(self)

		# Configure the event loop
		self.Loop.set_exception_handler(_loop_exception_handler)
		if Config["logging"].getboolean("verbose"):
			self.Loop.set_debug(True)
		
		try:
			# Signals are not available on Windows
			self.Loop.add_signal_handler(signal.SIGINT, self.stop)
		except NotImplementedError:
			# Checking if the program runs on Windows
			if any(platform.win32_ver()):
				if win32api is not None:
					callback = self.stop

					# Adding a handler to listen to the interrupt event
					def handler(type):
						callback()
						return True
					win32api.SetConsoleCtrlHandler(handler, True)

		try:
			self.Loop.add_signal_handler(signal.SIGTERM, self.stop)
		except NotImplementedError:
			pass

		try:
			self.Loop.add_signal_handler(signal.SIGHUP, self._hup)
		except NotImplementedError:
			pass

		self._stop_event = asyncio.Event(loop = self.Loop)
		self._stop_event.clear()
		self._stop_counter = 0

		from .pubsub import PubSub
		self.PubSub = PubSub(self)

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


	def create_argument_parser(self):
		'''
		This method can be overriden to adjust argparse configuration 
		'''

		parser = argparse.ArgumentParser(
			formatter_class=argparse.RawDescriptionHelpFormatter,
			description=self.Description,
		)
		parser.add_argument('-c', '--config', help='specify a path to a configuration file')
		parser.add_argument('-v', '--verbose', action='store_true', help='print more information (enable debug output)')
		parser.add_argument('-s', '--syslog', action='store_true', help='enable logging to a syslog')
		parser.add_argument('-l', '--log-file', help='specify a path to a log file')

		if daemon is not None:
			parser.add_argument('-d', '--daemonize', action='store_true', help='run daemonized (in the background)')
			parser.add_argument('-k', '--kill', action='store_true', help='kill a running daemon and quit')

		return parser


	def parse_arguments(self):
		parser = self.create_argument_parser()
		args = parser.parse_args()

		if args.config is not None:
			Config._default_values['general']['config_file'] = args.config

		if args.verbose:
			Config._default_values['logging']['verbose'] = True

		if args.syslog:
			Config._default_values['logging:syslog']['enabled'] = True

		if args.log_file:
			Config._default_values['logging:file']['path'] = args.log_file

		return args


	def get_pidfile_path(self):
		pidfilepath = Config['general']['pidfile']
		if pidfilepath == "":
			return None
		elif pidfilepath == "!":
			return os.path.join('/var/run', os.path.basename(sys.argv[0]) + '.pid')
		else:
			return pidfilepath


	def daemonize(self):
		if daemon is None:
			print("Install 'python-daemon' module to support daemonising.", file=sys.stderr)
			sys.exit(1)

		pidfilepath = self.get_pidfile_path()
		if pidfilepath is not None:
			pidfile = daemon.pidfile.TimeoutPIDLockFile(pidfilepath)


		working_dir = Config['general']['working_dir']

		uid = Config['general']['uid']
		if uid == "": uid = None

		gid = Config['general']['gid']
		if gid == "": gid = None

		signal_map={
			signal.SIGTTIN: None,
			signal.SIGTTOU: None,
			signal.SIGTSTP: None,
		}

		self.DaemonContext = daemon.DaemonContext(
			working_directory=working_dir,
			signal_map=signal_map,
			pidfile=pidfile,
			uid=uid,
			gid=gid,
		)

		try:
			self.DaemonContext.open()
		except lockfile.AlreadyLocked as e:
			print("Cannot create a PID file '{}':".format(pidfilepath), e, file=sys.stderr)
			sys.exit(1)


	def daemon_kill(self):
		if daemon is None:
			print("Install 'python-daemon' module to support daemonising.", file=sys.stderr)
			sys.exit(1)

		pidfilepath = self.get_pidfile_path()
		if pidfilepath is None:
			sys.exit(0)

		try:
			pid = open(pidfilepath, "r").read()
		except FileNotFoundError:
			print("Pid file '{}' not found.".format(pidfilepath), file=sys.stderr)
			sys.exit(0)

		pid = int(pid)

		for sno in [signal.SIGINT, signal.SIGINT, signal.SIGINT, signal.SIGINT, signal.SIGTERM]:
			try:
				os.kill(pid, sno)
			except ProcessLookupError:
				print("Process with pid '{}' not found.".format(pid), file=sys.stderr)
				sys.exit(0)
			for i in range(10):
				if not os.path.exists(pidfilepath):
					sys.exit(0)
				time.sleep(0.1)
			print("Daemon process (pid: {}) still running ...".format(pid), file=sys.stderr)

		print("Pid file '{}' not found.".format(pidfilepath), file=sys.stderr)
		sys.exit(1)



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
			except BaseException:
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
			except BaseException:
				L.exception("Exception in {}".format(task))

		#TODO: Process pending_tasks tasks from above (should be none)

		# Python 3.5 lacks support for shutdown_asyncgens()
		if hasattr(self.Loop, "shutdown_asyncgens"):
			self.Loop.run_until_complete(self.Loop.shutdown_asyncgens())
		self.Loop.close()

		return self.ExitCode


	def stop(self, exit_code:int=None):
		if exit_code is not None:
			self.set_exit_code(exit_code)

		self._stop_event.set()
		self._stop_counter += 1
		self.PubSub.publish("Application.stop!", self._stop_counter)
		if self._stop_counter >= 3:
			L.fatal("Emergency exit")
			try:
				# EX_SOFTWARE code is not available on Windows
				return os._exit(os.EX_SOFTWARE)
			except AttributeError:
				return os._exit(0)


	def _hup(self):
		self.Logging.rotate()
		self.PubSub.publish("Application.hup!")


	# Modules

	def add_module(self, module_class):
		""" Load a new module. """

		for module in self.Modules:
			if isinstance(module, module_class):
				# Already loaded and registered
				return

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


	def _register_service(self, service):
		""" Register a new service using its name. """

		if service.Name in self.Services:
			L.error("Service '{}' already registered (existing:{} new:{})"
					.format(service.Name, self.Services[service.Name], service))
			raise RuntimeError("Service {} already registered".format(service.Name))

		self.Services[service.Name] = service

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

		tasks_awaiting = 0
		for i in range(3):
			ts = asyncio.Task.all_tasks(self.Loop)
			tasks_awaiting = 0
			for t in ts:
				if t.done(): continue
				tasks_awaiting += 1
			if tasks_awaiting <= 2:
				# 2 is for _exit_time_governor and wait()
				break

			await asyncio.sleep(1)

		else:
			L.warn("Exiting but {} async task(s) are still waiting".format(tasks_awaiting))

		future.set_result("exit")


	def set_exit_code(self, exit_code:int, force:bool=False):
		if (self.ExitCode < exit_code) or force:
			L.debug("Exit code set to {}",format(exit_code))
			self.ExitCode = exit_code
