import os
import sys
import time
import signal
import random
import logging
import asyncio
import argparse
import itertools
import platform
import datetime
import typing

import threading

import asab

try:
	import daemon
	import daemon.pidfile
	import lockfile
except ImportError:
	daemon = None

from .config import Config
from .abc.singleton import Singleton
from .log import Logging, _loop_exception_handler, LOG_NOTICE
from .task import TaskService

L = logging.getLogger(__name__)


class Application(metaclass=Singleton):
	"""The base application object that maintains the global application state.

	You can provide your own implementation by creating a subclass. It is intended to be a Singleton.

	Examples:
	```python
	class MyApplication(asab.Application):
		async def main(self):
			print("Hello world!")
			self.stop()

	if __name__ == "__main__":
		app = MyApplication()
		app.run()
	```
	"""

	Description = "This app is based on ASAB."

	def __init__(self, args: typing.Optional[list] = None, modules: list = []):
		"""
		Initialize the Application provided with arguments and modules.

		Args:
			args: sequence of arguments to be parsed by `Application.parse_arguments()` call.
			modules: list of ASAB modules to be added by `Application.add_module()` call.

		Examples:

		```python
		class MyApplication(asab.Application):
			def __init__(self):
				super().__init__(modules=[asab.web.Module, asab.zookeeper.Module])
		```
		"""

		self.ExitCode: typing.Union[int, str]
		"""
		The actual value of the exit code that can be set via `set_exit_code()` method.

		Examples:
			The example of the exit code handling in the `main()` function of the application:

			```python
			if __name__ == '__main__':
				app = asab.Application()
				exit_code = app.run()
				sys.exit(exit_code)
			```

			| Exit code | Meaning |
			| --- | --- |
			| 0 | success |
			| 1 | abnormal termination of a program perhaps as a result a minor problem in the code |
			| "!RESTART!" | hard restart of the whole application |

		"""

		try:
			# EX_OK code is not available on Windows
			self.ExitCode = os.EX_OK
		except AttributeError:
			self.ExitCode = 0

		# Queue of Services to be initialized
		self.InitServicesQueue = []
		# Queue of Modules to be initialized
		self.InitModulesQueue = []

		# Parse command line
		self.Args = self.parse_arguments(args=args)

		# Obtain HostName
		# The user can provide the actual hostname of the application in ASAB_HOSTNAME environment variable.
		# This can be used to specify the hostname that is discoverable by other services in a cluster, if a local hostname is not suitable.
		self.HostName = os.environ.get('ASAB_HOSTNAME', None)
		if self.HostName is None:
			self.HostName = platform.node()
		os.environ['HOSTNAME'] = self.HostName

		# Load configuration
		Config._load()

		if hasattr(self.Args, "daemonize") and self.Args.daemonize:
			self.daemonize()

		elif hasattr(self.Args, "kill") and self.Args.kill:
			self.daemon_kill()

		# Seed the random generator
		random.seed()

		# Obtain the event loop
		self.Loop = asyncio.get_event_loop()
		if self.Loop.is_closed():
			self.Loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self.Loop)

		self.LaunchTime = time.time()
		self.BaseTime = self.LaunchTime - self.Loop.time()

		# Last time the on_tick/60! was registered
		self.LastOnTick60 = self.LaunchTime

		self.Modules: list[asab.Module] = []
		"""
		A list of modules that has been added to the application.
		"""

		self.Services: dict[str, asab.Service] = {}
		"""
		A dictionary of registered services.
		"""

		# Setup logging
		self.Logging = Logging(self)

		# Configure the event loop
		self.Loop.set_exception_handler(_loop_exception_handler)
		if Config["logging"].getboolean("verbose"):
			self.Loop.set_debug(True)

		# Adding a handler to listen to the interrupt event
		if platform.system() == "Windows":

			try:

				# Windows win32api import
				import win32api

				def handler(type):
					self.stop()
					return True

				win32api.SetConsoleCtrlHandler(handler, True)

			except ImportError as e:
				L.warning("win32api module could not be loaded, because '{}'".format(
					e
				))

		else:

			# POSIX and other reasonable systems
			self.Loop.add_signal_handler(signal.SIGINT, self.stop)
			self.Loop.add_signal_handler(signal.SIGTERM, self.stop)
			self.Loop.add_signal_handler(signal.SIGHUP, self._hup)

		self._stop_event = asyncio.Event()
		self._stop_event.clear()
		self._stop_counter = 0

		from .pubsub import PubSub
		self.PubSub = PubSub(self)

		L.info("Initializing ...")

		self.TaskService = TaskService(self)

		for module in modules:
			self.add_module(module)

		# Set housekeeping time and time limit
		self.HousekeepingTime, self.HousekeepingTimeLimit, self.HousekeepingId = self._initialize_housekeeping_schedule()
		self.HousekeepingMissedEvents: list = []
		# Every 10 minutes listen for housekeeping
		self.PubSub.subscribe("Application.tick/600!", self._on_housekeeping_tick)

		# Run the watchdog to detect lost interactivity on the event loop
		self.WatchdogThreshold = Config["general"].getseconds("watchdog_threshold")

		if self.WatchdogThreshold > 0:
			watchdog_thread = threading.Thread(target=self._watchdog)
			watchdog_thread.daemon = True  # Daemonize the thread to ensure it exits with the main program
			watchdog_thread.start()


	def _watchdog(self):
		"""
		Periodically checks the loop interactivity
		and if the configured threshold is passed,
		the application is killed by a signal.
		"""

		while True:
			current_time = time.time()

			# Check if the configured threshold passed
			if (current_time - self.LastOnTick60) < self.WatchdogThreshold:
				time.sleep(60)  # Sleep one minute (one cycle)
				continue

			# The loop lost its interactivity
			L.critical("The event loop lost its interactivity. Stopping the application!")
			os.kill(os.getpid(), signal.SIGKILL)  # Works only on Linux
			os._exit(5)  # Cannot use sys.exit inside the thread


	def create_argument_parser(
		self,
		prog=None,
		usage=None,
		description=None,
		epilog=None,
		prefix_chars='-',
		fromfile_prefix_chars=None,
		argument_default=None,
		conflict_handler='error',
		add_help=True
	) -> argparse.ArgumentParser:
		"""
		Create an `argparse.ArgumentParser` object supplemented by default ASAB arguments.

		This method can be overridden to adjust argparse configuration.
		Refer to the Python standard library to [`argparse.ArgumentParser`](https://docs.python.org/3/library/argparse.html?highlight=argumentparser#argumentparser-objects) for the details.
		"""

		parser = argparse.ArgumentParser(
			prog=prog,
			usage=usage,
			description=description if description is not None else self.Description,
			epilog=epilog,
			formatter_class=argparse.RawDescriptionHelpFormatter,
			prefix_chars=prefix_chars,
			fromfile_prefix_chars=fromfile_prefix_chars,
			argument_default=argument_default,
			conflict_handler=conflict_handler,
			add_help=add_help
		)
		parser.add_argument('-c', '--config', help='specify a path to a configuration file')
		parser.add_argument('-v', '--verbose', action='store_true', help='print more information (enable debug output)')
		parser.add_argument('-s', '--syslog', action='store_true', help='enable logging to a syslog')
		parser.add_argument('-l', '--log-file', help='specify a path to a log file')
		parser.add_argument('-w', '--web-api', help='activate Asab web API (default listening port is 0.0.0.0:8080)', const="0.0.0.0:8080", nargs="?")
		parser.add_argument('--startup-housekeeping', help='trigger housekeeping event immediately after application startup')
		parser.add_argument('--no-auth', action='store_true', help='disable all authentication and authorization')


		if daemon is not None:
			parser.add_argument('-d', '--daemonize', action='store_true', help='run daemonized (in the background)')
			parser.add_argument('-k', '--kill', action='store_true', help='kill a running daemon and quit')

		return parser


	def parse_arguments(self, args=None):
		"""
		Parse the command line arguments and set the default values for the configuration accordingly.

		Args:
			args: The arguments to parse. If not set, sys.argv[1:] will be used.

		Returns:
			The arguments that were parsed.
		"""

		parser = self.create_argument_parser()
		args = parser.parse_args(args=args)

		if args.config is not None:
			Config._default_values['general']['config_file'] = args.config

		if args.verbose:
			Config._default_values['logging']['verbose'] = True

		if args.syslog:
			Config._default_values['logging:syslog']['enabled'] = True

		if args.log_file:
			Config._default_values['logging:file']['path'] = args.log_file

		if args.web_api:
			if 'web' not in Config._default_values:
				Config._default_values['web'] = {}
			Config._default_values['web']['listen'] = args.web_api

		if args.no_auth:
			if 'auth' not in Config._default_values:
				Config._default_values['auth'] = {}
			Config._default_values['auth']['enabled'] = False

		if args.startup_housekeeping:
			Config._default_values['housekeeping']['run_at_startup'] = True

		return args


	def get_pidfile_path(self) -> typing.Optional[str]:
		"""
		Get the path for PID file from the configuration.

		PID file is a file that contains process id of the ASAB process.
		It is used for interaction with OS respective it's control of running services.

		- If the `pidfile` is set to the empty string, return None.
		- If `pidfile` is set to "!", return the default PID file path (in `/var/run/` folder).
		This is the default value.

		Example of PID path configuration:

		```ini
		[general]
		pidfile=/tmp/my.pid
		```

		Returns:
			The path to the `pidfile`.
		"""

		pidfilepath = Config['general']['pidfile']
		if pidfilepath == "":
			return None
		elif pidfilepath == "!":
			return os.path.join('/var/run', os.path.basename(sys.argv[0]) + '.pid')
		else:
			return pidfilepath


	def daemonize(self):
		if daemon is None:
			print("Install 'python-daemon' module to support daemonizing.", file=sys.stderr)
			sys.exit(1)

		pidfilepath = self.get_pidfile_path()
		if pidfilepath is not None:
			pidfile = daemon.pidfile.TimeoutPIDLockFile(pidfilepath)

		working_dir = Config['general']['working_dir']

		uid = Config['general']['uid']
		if uid == "":
			uid = None

		gid = Config['general']['gid']
		if gid == "":
			gid = None

		signal_map = {
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
		"""Run the application.

		Returns:
			(int): Exit code of the finalized process.
		"""

		# Commence init-time
		self.PubSub.publish("Application.init!")
		self.Loop.run_until_complete(asyncio.gather(
			self._init_time_governor(),
			self.initialize(),

		))

		try:
			# Commence run-time and application main() function
			L.log(LOG_NOTICE, "is ready.")
			self._stop_event.clear()
			self.Loop.run_until_complete(asyncio.gather(
				self._run_time_governor(),
				self.main(),
			))

			# Comence exit-time
			if self.ExitCode == "!RESTART!":
				L.log(LOG_NOTICE, "is restarting ...")
			else:
				L.log(LOG_NOTICE, "is exiting ...", struct_data={'exit_code': self.ExitCode})
			self.Loop.run_until_complete(asyncio.gather(
				self.finalize(),
				self._exit_time_governor(),
			))

			# Python 3.5 lacks support for shutdown_asyncgens()
			if hasattr(self.Loop, "shutdown_asyncgens"):
				self.Loop.run_until_complete(self.Loop.shutdown_asyncgens())
			self.Loop.close()

		finally:
			if self.ExitCode == "!RESTART!":
				os.execv(sys.executable, [os.path.basename(sys.executable)] + sys.argv)

		return self.ExitCode


	def stop(self, exit_code: typing.Optional[int] = None) -> None:
		"""
		Gracefully terminate the _run-time_ and commence the _exit-time_.

		This method is automatically called by `SIGINT` and `SIGTERM`.
		It also includes a response to `Ctrl-C` on UNIX-like system.
		When this method is called 3x, it abruptly exits the application (aka emergency abort).

		Args:
			exit_code (int, optional): Exit code of the finalized process.
		"""

		if exit_code is not None:
			self.set_exit_code(exit_code)

		self._stop_event.set()
		self._stop_counter += 1
		self.PubSub.publish("Application.stop!", self._stop_counter)

		if self._stop_counter >= 3:
			L.fatal("Emergency exit")
			for task in asyncio.all_tasks():
				L.warning("Pending task during emergency exit: {}".format(task))
			try:
				# EX_SOFTWARE code is not available on Windows
				return os._exit(os.EX_SOFTWARE)
			except AttributeError:
				return os._exit(0)

		elif self._stop_counter > 1:
			L.warning("{} tasks still active".format(len(asyncio.all_tasks())), struct_data={"count": self._stop_counter})


	def _do_restart(self, event_name):
		self.stop("!RESTART!")


	def restart(self):
		"""
		Schedule a hard restart of the whole application.

		This function works by using `os.execv()`, which replaces the current process with a new one (without creating a new process ID).
		Arguments and environment variables will be retained.

		!!! warning
			Please note that this will work on Unix-based systems only, as it uses a feature specific to Unix.

		!!! hint
			Be careful while using this function, make sure you have some control
			over when and how this function is being called to avoid any unexpected process restarts.
			It is not common to use these types of function calls in Python applications.
		"""
		self.PubSub.subscribe("Application.tick/10!", self._do_restart)


	def _hup(self):
		self.Logging.rotate()
		self.PubSub.publish("Application.hup!")


	# Modules

	def add_module(self, module_class: asab.Module) -> None:
		"""
		Load a new module.
		"""

		for module in self.Modules:
			if isinstance(module, module_class):
				# Already loaded and registered
				return

		module = module_class(self)
		self.Modules.append(module)

		# Enqueue module for initialization (happens in run phase)
		self.InitModulesQueue.append(module)


	# Services

	def get_service(self, service_name: str) -> typing.Optional[asab.Service]:
		"""
		Get a new service by its name.

		Args:
			service_name: Name of the service to retrieve.

		Returns:
			The service object associated with the provided service_name,
			or None if the service is not registered.
		"""
		return self.Services.get(service_name)


	def _register_service(self, service: asab.Service):
		"""
		Register a new service using its name.
		"""

		if service.Name in self.Services:
			L.error("Service '{}' already registered (existing:{} new:{})".format(
				service.Name, self.Services[service.Name], service))
			raise RuntimeError("Service {} already registered".format(service.Name))

		self.Services[service.Name] = service

		# Enqueue service for initialization (happens in run phase)
		self.InitServicesQueue.append(service)


	# Lifecycle callback

	async def initialize(self):
		"""
		This method is called during the application *init-time*. It is intended to be overridden by the user.
		"""
		pass

	async def main(self):
		"""
		This method is called during the application *run-time*. It is intended to be overridden by the user.
		"""
		pass

	async def finalize(self):
		"""
		This method is called during the application *exit-time*. It is intended to be overridden by the user.
		"""
		pass


	# Governors

	async def _init_time_governor(self):
		"""
		Initialize all services that has been created during application construction
		"""
		await self._ensure_initialization()


	async def _run_time_governor(self):
		timeout = Config.getint('general', 'tick_period')
		self.PubSub.publish("Application.run!")

		if Config.getboolean("housekeeping", "run_at_startup", fallback=False):
			L.log(asab.LOG_NOTICE, "Startup housekeeping...")
			self.PubSub.publish("Application.housekeeping!")

		# Wait for stop event & tick in meanwhile
		for cycle_no in itertools.count(1):

			await self._ensure_initialization()

			try:
				await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
				break
			except asyncio.TimeoutError:
				self.PubSub.publish("Application.tick!")
				if (cycle_no % 10) == 0:
					self.PubSub.publish("Application.tick/10!")
				if (cycle_no % 60) == 0:
					# Rebase a Loop time
					current_time = time.time()
					self.LastOnTick60 = current_time
					self.BaseTime = current_time - self.Loop.time()
					self.PubSub.publish("Application.tick/60!")
				if (cycle_no % 300) == 0:
					self.PubSub.publish("Application.tick/300!")
				if (cycle_no % 600) == 0:
					self.PubSub.publish("Application.tick/600!")
				if (cycle_no % 1800) == 0:
					self.PubSub.publish("Application.tick/1800!")
				if (cycle_no % 3600) == 0:
					self.PubSub.publish("Application.tick/3600!")
				if (cycle_no % 43200) == 0:
					self.PubSub.publish("Application.tick/43200!")
				if (cycle_no % 86400) == 0:
					self.PubSub.publish("Application.tick/86400!")
				continue


	async def _exit_time_governor(self):
		self.PubSub.publish("Application.exit!")

		# Finalize services
		for service in reversed(self.Services.values()):
			try:
				await service.finalize(self)
			except Exception:
				L.exception("Error during service finalize call")

		# Finalize modules
		for module in reversed(self.Modules):
			try:
				await module.finalize(self)
			except Exception:
				L.exception("Error during module finalize call")

		# Wait for non-finalized tasks
		tasks_awaiting = 0
		for i in range(3):
			try:
				ts = asyncio.all_tasks(self.Loop)
			except AttributeError:
				# Compatibility for Python 3.6-
				ts = asyncio.Task.all_tasks(self.Loop)
			tasks_awaiting = 0
			for t in ts:
				if t.done():
					continue
				tasks_awaiting += 1
			if tasks_awaiting <= 1:
				# 2 is for _exit_time_governor and wait()
				break

			await asyncio.sleep(1)

		else:
			L.warning("Exiting but {} async task(s) are still waiting".format(tasks_awaiting))


	async def _ensure_initialization(self):
		'''
		This method ensures that any newly add module or registered service is initialized.
		It is called from:
		(1) init-time for modules&services added during application construction.
		(2) run-time for modules&services added during aplication lifecycle.
		'''

		# Initialize modules
		while len(self.InitModulesQueue) > 0:
			module = self.InitModulesQueue.pop()
			try:
				await module.initialize(self)
			except Exception:
				L.exception("Error during module initialization")

		# Initialize services
		while len(self.InitServicesQueue) > 0:
			service = self.InitServicesQueue.pop()
			try:
				await service.initialize(self)
			except Exception:
				L.exception("Error during service initialization")


	def set_exit_code(self, exit_code: typing.Union[int, str], force: bool = False):
		"""
		Set the exit code of the application.

		If `force` is `False`, the exit code will be set only if the previous value is lower than the new one.
		If `force` is `True`, the exit code value is set to `exit_code` value disregarding the previous value.

		Args:
			exit_code (str | int): The exit code value.
			force: Force the exit code reassignment.
		"""
		if self.ExitCode == "!RESTART!":
			return

		if exit_code == "!RESTART!":
			self.ExitCode = exit_code

		elif (self.ExitCode < exit_code) or force:
			L.debug("Exit code set to {}".format(exit_code))
			self.ExitCode = exit_code


	# Time

	def time(self) -> float:
		"""
		Return UTC UNIX timestamp using a loop time (a fast way how to get a wall clock time).

		Returns:
			Current UTC UNIX timestamp.
		"""
		return self.BaseTime + self.Loop.time()


	# Housekeeping

	def _initialize_housekeeping_schedule(self):
		"""
		Set the next housekeeping time and time limit from configuration.

		Returns:
			(next_housekeeping_time, next_time_limit, next_housekeeping_id)
		"""
		config_house_time = datetime.datetime.strptime(Config['housekeeping']['at'], "%H:%M")  # default: 03:00
		config_time_limit = datetime.datetime.strptime(Config['housekeeping']['limit'], "%H:%M")  # default: 05:00

		now = datetime.datetime.now(datetime.timezone.utc)

		next_housekeeping_time = now.replace(
			hour=config_house_time.hour,
			minute=config_house_time.minute,
			second=0,
			microsecond=0)

		# if the app started after the housekeeping time, set it to the next day
		if now > next_housekeeping_time:
			next_housekeeping_time += datetime.timedelta(days=1)

		# compute the time limit for the housekeeping
		time_delta_limit = config_time_limit - config_house_time
		if time_delta_limit < datetime.timedelta(hours=0):
			time_delta_limit += datetime.timedelta(days=1)

		next_time_limit = next_housekeeping_time + time_delta_limit

		# Each time has its id that prevents from accidental executing housekeeping twice.
		next_housekeeping_id = _housekeeping_id(now)


		return (next_housekeeping_time, next_time_limit, next_housekeeping_id)

	def _on_housekeeping_tick(self, message_type):
		"""
		Check if it's time for publishing the 'Application.housekeeping!' message.
		If so, publish the message and set housekeeping time, the time limit and time id for the next day.
		"""
		now = datetime.datetime.now(datetime.timezone.utc)
		today_id = _housekeeping_id(now)

		if self.HousekeepingTime < now:
			if now < self.HousekeepingTimeLimit and self.HousekeepingId <= today_id:
				L.log(asab.LOG_NOTICE, "Housekeeping started.")
				self.PubSub.publish("Application.housekeeping!")
			else:
				L.error(
					"Housekeeping has not been executed: It is past the time limit.",
					struct_data={
						"housekeeping_time": self.HousekeepingTime.strftime("%Y-%m-%d %H:%M:%S"),
						"time_limit": self.HousekeepingTimeLimit.strftime("%Y-%m-%d %H:%M:%S"),
						"housekeeping_id": self.HousekeepingId,
					}
				)
				self.HousekeepingMissedEvents.append(today_id)

			self.HousekeepingTime += datetime.timedelta(days=1)
			self.HousekeepingTimeLimit += datetime.timedelta(days=1)
			self.HousekeepingId = _housekeeping_id(self.HousekeepingTime)

			if len(self.HousekeepingMissedEvents) > 0:
				L.error(
					"One or more Housekeeping events have not been executed.",
					struct_data={
						"missed_housekeeping_events": self.HousekeepingMissedEvents
					})


def _housekeeping_id(dt: datetime.datetime) -> int:
	"""
	Create a unique ID for each date. Utility function for housekeeping.

	>>> housekeeping_id(datetime.datetime.now())
	20230418
	"""
	return int(dt.strftime("%Y%m%d"))
