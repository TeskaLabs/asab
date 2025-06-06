import asyncio
import datetime
import logging
import logging.handlers
import json
import os
import pprint
import queue
import re
import socket
import sys
import time
import traceback
import urllib.parse

from .config import Config
from .timer import Timer
from .utils import running_in_container


LOG_NOTICE = 25
"""
Info log level that is visible in non-verbose mode. It should not be used for warnings and errors.
"""

logging.addLevelName(LOG_NOTICE, "NOTICE")

L = logging.getLogger(__name__)

_NAME_TO_LEVEL = {
	"NOTSET": logging.NOTSET,
	"NOT SET": logging.NOTSET,
	"NOT_SET": logging.NOTSET,
	"DEBUG": logging.DEBUG,
	"INFO": logging.INFO,
	"NOTICE": LOG_NOTICE,
	"LOG_NOTICE": LOG_NOTICE,
	"LOG NOTICE": LOG_NOTICE,
	"WARNING": logging.WARNING,
	"WARN": logging.WARNING,
	"ERROR": logging.ERROR,
	"FATAL": logging.CRITICAL,
	"CRITICAL": logging.CRITICAL,
}


class Logging(object):


	def __init__(self, app):
		self.RootLogger = logging.getLogger()

		self.ConsoleHandler = None
		self.FileHandler = None
		self.SyslogHandler = None

		if not self.RootLogger.hasHandlers():

			# Add console logger if needed
			if os.isatty(sys.stdout.fileno()) or os.environ.get('ASABFORCECONSOLE', '0') != '0' or Config.getboolean("logging:console", "enabled"):
				self._configure_console_logging()

			# Initialize file handler
			file_path = Config["logging:file"]["path"]

			if len(file_path) > 0:

				# Ensure file path
				directory = os.path.dirname(file_path)
				if not os.path.exists(directory):
					os.makedirs(directory)

				self.FileHandler = logging.handlers.RotatingFileHandler(
					file_path,
					backupCount=Config.getint("logging:file", "backup_count"),
					maxBytes=Config.getint("logging:file", "backup_max_bytes"),
				)
				self.FileHandler.setLevel(logging.DEBUG)
				self.FileHandler.setFormatter(StructuredDataFormatter(
					fmt=Config["logging:file"]["format"],
					datefmt=Config["logging:file"]["datefmt"],
					sd_id=Config["logging"]["sd_id"],
				))
				self.RootLogger.addHandler(self.FileHandler)

				rotate_every = Config.get("logging:file", "rotate_every")
				if rotate_every != '':
					rotate_every = re.match(r"^([0-9]+)([dMHs])$", rotate_every)
					if rotate_every is not None:
						i, u = rotate_every.groups()
						i = int(i)
						if i <= 0:
							self.RootLogger.error("Invalid 'rotate_every' configuration value.")
						else:
							if u == 'H':
								i = i * 60 * 60
							elif u == 'M':
								i = i * 60
							elif u == 'd':
								i = i * 60 * 60 * 24
							elif u == 's':
								pass

							# PubSub is not ready at this moment, we need to create timer in a future
							async def schedule(app, interval):
								self.LogRotatingTime = Timer(app, self._on_tick_rotate_check, autorestart=True)
								self.LogRotatingTime.start(i)
							asyncio.ensure_future(schedule(app, i))

					else:
						self.RootLogger.error("Invalid 'rotate_every' configuration value.")

			# Initialize syslog
			if Config["logging:syslog"].getboolean("enabled"):

				address = Config["logging:syslog"]["address"]

				if address[:1] == '/':
					self.SyslogHandler = AsyncIOHandler(app.Loop, socket.AF_UNIX, socket.SOCK_DGRAM, address)

				else:
					url = urllib.parse.urlparse(address)

					if url.scheme == 'tcp':
						self.SyslogHandler = AsyncIOHandler(app.Loop, socket.AF_INET, socket.SOCK_STREAM, (
							url.hostname if url.hostname is not None else 'localhost',
							url.port if url.port is not None else logging.handlers.SYSLOG_UDP_PORT
						))

					elif url.scheme == 'udp':
						self.SyslogHandler = FormatingDatagramHandler(
							url.hostname if url.hostname is not None else 'localhost',
							url.port if url.port is not None else logging.handlers.SYSLOG_UDP_PORT
						)

					elif url.scheme == 'unix-connect':
						self.SyslogHandler = AsyncIOHandler(app.Loop, socket.AF_UNIX, socket.SOCK_STREAM, url.path)

					elif url.scheme == 'unix-sendto':
						self.SyslogHandler = AsyncIOHandler(app.Loop, socket.AF_UNIX, socket.SOCK_DGRAM, url.path)

					else:
						self.RootLogger.warning("Invalid logging:syslog address '{}'".format(address))
						address = None

				if self.SyslogHandler is not None:
					self.SyslogHandler.setLevel(logging.DEBUG)
					format = Config["logging:syslog"]["format"]
					if format == 'm':
						self.SyslogHandler.setFormatter(MacOSXSyslogFormatter(sd_id=Config["logging"]["sd_id"]))
					elif format == '5':
						self.SyslogHandler.setFormatter(SyslogRFC5424Formatter(sd_id=Config["logging"]["sd_id"]))
					elif format == '5micro':
						self.SyslogHandler.setFormatter(SyslogRFC5424microFormatter(sd_id=Config["logging"]["sd_id"]))
					elif format == 'json':
						self.SyslogHandler.setFormatter(JSONFormatter())
					else:
						self.SyslogHandler.setFormatter(SyslogRFC3164Formatter(sd_id=Config["logging"]["sd_id"]))
					self.RootLogger.addHandler(self.SyslogHandler)

			# No logging is configured
			if self.ConsoleHandler is None and self.FileHandler is None and self.SyslogHandler is None:
				# Let's check if we run in Docker and if so, then log on stderr
				if running_in_container():
					self._configure_console_logging()

		else:
			self.RootLogger.warning("Logging seems to be already configured. Proceed with caution.")

		if Config["logging"].getboolean("verbose"):
			self.RootLogger.setLevel(2)
		else:
			level_name = Config["logging"]["level"].upper()
			try:
				self.RootLogger.setLevel(_NAME_TO_LEVEL.get(level_name, level_name))
			except ValueError:
				L.error("Cannot detect logging level '{}'".format(level_name))

		# Fine-grained log level configurations
		levels = Config["logging"].get('levels')
		for level_line in levels.split('\n'):
			level_line = level_line.strip()
			if len(level_line) == 0 or level_line.startswith('#') or level_line.startswith(';'):
				# line starts with a comment
				continue
			try:
				logger_name, level_name = level_line.split(' ', 1)
			except ValueError:
				L.error("Cannot read line '{}' in '[logging] levels' section, expected format: 'logger_name level_name'.".format(level_line))
				continue
			level = _NAME_TO_LEVEL.get(level_name.upper(), level_name.upper())
			try:
				logging.getLogger(logger_name).setLevel(level)
			except ValueError:
				L.error("Cannot detect logging level '{}' for {} logger".format(level_name, logger_name))

	def rotate(self):
		if self.FileHandler is not None:
			self.RootLogger.log(LOG_NOTICE, "Rotating logs")
			self.FileHandler.doRollover()


	async def _on_tick_rotate_check(self):
		if self.FileHandler is not None:
			if self.FileHandler.stream.tell() > 1000:
				self.rotate()


	def _configure_console_logging(self):
		self.ConsoleHandler = logging.StreamHandler(stream=sys.stderr)

		# Disable colors when running in container
		if running_in_container():
			self.ConsoleHandler.setFormatter(StructuredDataFormatter(
				fmt=Config["logging:console"]["format"],
				datefmt=Config["logging:console"]["datefmt"],
				sd_id=Config["logging"]["sd_id"],
				use_color=False
			))
		else:
			self.ConsoleHandler.setFormatter(StructuredDataFormatter(
				fmt=Config["logging:console"]["format"],
				datefmt=Config["logging:console"]["datefmt"],
				sd_id=Config["logging"]["sd_id"],
				use_color=True
			))

		self.ConsoleHandler.setLevel(logging.DEBUG)
		self.RootLogger.addHandler(self.ConsoleHandler)


class _StructuredDataLogger(logging.Logger):
	'''
This class extends a default python logger class, specifically by adding ``struct_data`` parameter to logging functions.
It means that you can use expressions such as ``logger.info("Hello world!", struct_data={'key':'value'})``.
	'''

	def _log(self, level, msg, args, exc_info=None, struct_data=None, extra=None, stack_info=False):
		if struct_data is not None:
			if extra is None:
				extra = dict()
			extra['_struct_data'] = struct_data

		super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)


logging.setLoggerClass(_StructuredDataLogger)


class StructuredDataFormatter(logging.Formatter):
	'''
	The logging formatter that renders log messages that includes structured data.
	'''

	empty_sd = ""
	BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


	def __init__(self, facility=16, fmt=None, datefmt=None, style='%', sd_id='sd', use_color: bool = False):
		# Because of custom formatting, the style is set to percent style and cannot be changed.
		style = '%'
		super().__init__(fmt, datefmt, style)
		self.SD_id = sd_id
		self.Facility = facility
		self.UseColor = use_color

	def formatMessage(self, record):
		values = record.__dict__.copy()
		values["struct_data"] = self.render_struct_data(values.get("_struct_data"))

		# The Priority value is calculated by first multiplying the Facility number by 8 and then adding the numerical value of the Severity.
		if record.levelno <= logging.DEBUG:
			severity = 7  # Debug
			color = self.BLUE
		elif record.levelno <= logging.INFO:
			severity = 6  # Informational
			color = self.GREEN
		elif record.levelno <= LOG_NOTICE:
			severity = 5  # Notice
			color = self.CYAN
		elif record.levelno <= logging.WARNING:
			severity = 4  # Warning
			color = self.YELLOW
		elif record.levelno <= logging.ERROR:
			severity = 3  # Error
			color = self.RED
		elif record.levelno <= logging.CRITICAL:
			severity = 2  # Critical
			color = self.MAGENTA
		else:
			severity = 1  # Alert
			color = self.WHITE

		if self.UseColor:
			levelname = record.levelname
			levelname_color = _COLOR_SEQ % (30 + color) + levelname + _RESET_SEQ
			values["levelname"] = levelname_color

		values["priority"] = (self.Facility << 3) + severity

		# We use percent style formatting only
		return self._fmt % values

	def formatTime(self, record, datefmt=None):
		'''
		Return the creation time of the specified LogRecord as formatted text.
		'''

		try:
			ct = datetime.datetime.fromtimestamp(record.created)
			if datefmt is not None:
				s = ct.strftime(datefmt)
			else:
				t = ct.strftime("%Y-%m-%d %H:%M:%S")
				s = "%s.%03d" % (t, record.msecs)
			return s
		except BaseException as e:
			print("ERROR when logging: {}".format(e), file=sys.stderr)
			return str(ct)


	def render_struct_data(self, struct_data):
		'''
		Return the string with structured data.
		'''

		if struct_data is None:
			return self.empty_sd

		else:
			return "[{sd_id} {sd_params}] ".format(
				sd_id=self.SD_id,
				sd_params=" ".join(['{}="{}"'.format(key, val) for key, val in struct_data.items()]))



def _loop_exception_handler(loop, context):
	'''
	This is an logging exception handler for asyncio.
	It's purpose is to nicely log any unhandled excpetion that arises in the asyncio tasks.
	'''

	exception = context.pop('exception', None)

	message = context.pop('message', '')
	if len(message) > 0:
		message += '\n'

	if len(context) > 0:
		message += pprint.pformat(context)

	if exception is not None:
		ex_traceback = exception.__traceback__
		tb_lines = [line.rstrip('\n') for line in traceback.format_exception(exception.__class__, exception, ex_traceback)]
		message += '\n' + '\n'.join(tb_lines)

	logging.getLogger().error(message)


class MacOSXSyslogFormatter(StructuredDataFormatter):
	"""
	It implements Syslog formatting for Mac OSX syslog (aka format ``m``).
	"""

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id='sd'):
		fmt = '<%(priority)s>%(asctime)s {app_name}[{proc_id}]: %(levelname)s %(name)s %(struct_data)s%(message)s\000'.format(
			app_name=Config["logging"]["app_name"],
			proc_id=os.getpid(),
		)

		# Initialize formatter
		super().__init__(fmt=fmt, datefmt='%b %d %H:%M:%S', style=style, sd_id=sd_id)


class SyslogRFC3164Formatter(StructuredDataFormatter):
	"""
	Implementation of a legacy or BSD Syslog (RFC 3164) formatting (aka format ``3``).
	"""

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id='sd'):
		fmt = '<%(priority)s>%(asctime)s {hostname} {app_name}[{proc_id}]:%(levelname)s %(name)s %(struct_data)s%(message)s\000'.format(
			app_name=Config["logging"]["app_name"],
			hostname=socket.gethostname(),
			proc_id=os.getpid(),
		)

		# Initialize formatter
		super().__init__(fmt=fmt, datefmt='%b %d %H:%M:%S', style=style, sd_id=sd_id)


class SyslogRFC5424Formatter(StructuredDataFormatter):
	"""
	It implements Syslog formatting for Mac OSX syslog (aka format ``5``).
	"""

	empty_sd = " "

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id='sd'):
		fmt = '<%(priority)s>1 %(asctime)s.%(msecs)dZ {hostname} {app_name} {proc_id} %(name)s [log l="%(levelname)s"]%(struct_data)s%(message)s'.format(
			app_name=Config["logging"]["app_name"],
			hostname=socket.gethostname(),
			proc_id=os.getpid(),
		)

		# Initialize formatter
		super().__init__(fmt=fmt, datefmt='%Y-%m-%dT%H:%M:%S', style=style, sd_id=sd_id)

		# Convert time to GMT
		self.converter = time.gmtime


class SyslogRFC5424microFormatter(StructuredDataFormatter):
	"""
	It implements Syslog formatting for syslog (aka format ``micro``) in RFC5424micro format.
	"""

	empty_sd = "-"

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id='sd'):
		fmt = '<%(priority)s>1 %(asctime)sZ {hostname} {app_name} {proc_id} %(name)s [log l="%(levelname)s"]%(struct_data)s%(message)s'.format(
			app_name=Config["logging"]["app_name"],
			hostname=socket.gethostname(),
			proc_id=os.getpid(),
		)

		super().__init__(fmt=fmt, datefmt='%Y-%m-%dT%H:%M:%S.%f', style=style, sd_id=sd_id)
		self.converter = time.gmtime


class JSONFormatter(logging.Formatter):

	def __init__(self):
		self.Enricher = {}
		instance_id = os.environ.get("INSTANCE_ID")
		service_id = os.environ.get("SERVICE_ID")
		node_id = os.environ.get("NODE_ID")
		hostname = socket.gethostname()
		if instance_id is not None:
			self.Enricher["instance_id"] = instance_id
		if service_id is not None:
			self.Enricher["service_id"] = service_id
		if node_id is not None:
			self.Enricher["node_id"] = node_id
		if hostname is not None:
			self.Enricher["hostname"] = hostname

	def _default(self, obj):
		# If obj is not json serializable, convert it to string
		try:
			return str(obj)
		except Exception:
			raise TypeError("Error when logging. Object {} of type {} is not JSON serializable.".format(obj, type(obj)))

	def format(self, record):
		r_copy = record.__dict__.copy()
		r_copy.update(self.Enricher)
		return json.dumps(r_copy, default=self._default)


class FormatingDatagramHandler(logging.handlers.DatagramHandler):

	def __init__(self, host, port):
		super().__init__(host, port)

	def emit(self, record):
		"""
		Add formatting to DatagramHandler. See https://docs.python.org/3/library/logging.handlers.html
		"""
		try:
			msg = self.format(record).encode('utf-8')
			self.send(msg)
		except Exception:
			self.handleError(record)


class AsyncIOHandler(logging.Handler):
	"""
	A logging handler similar to a standard `logging.handlers.SocketHandler` that utilizes `asyncio`.
	It implements a queue for decoupling logging from a networking. The networking is fully event-driven via `asyncio` mechanisms.
	"""

	def __init__(self, loop, family, sock_type, address, facility=logging.handlers.SysLogHandler.LOG_LOCAL1):
		logging.Handler.__init__(self)

		self._family = family
		self._type = sock_type
		self._address = address
		self._loop = loop

		self._socket = None
		self._reset()

		self._queue = queue.Queue()

		self._loop.call_soon(self._connect, self._loop)


	def _reset(self):
		self._write_ready = False
		if self._socket is not None:
			self._loop.remove_writer(self._socket)
			self._loop.remove_reader(self._socket)
			self._socket.close()
			self._socket = None


	def _connect(self, loop):
		self._reset()

		try:
			self._socket = socket.socket(self._family, self._type)
			self._socket.setblocking(0)
			self._socket.connect(self._address)
		except Exception as e:
			print("Error when opening syslog connection to '{}'".format(self._address), e, file=sys.stderr)
			return

		self._loop.add_writer(self._socket, self._on_write)
		self._loop.add_reader(self._socket, self._on_read)

	def _on_write(self):
		self._write_ready = True
		self._loop.remove_writer(self._socket)

		while not self._queue.empty():
			msg = self._queue.get_nowait()
			try:
				self._socket.sendall(msg)
			except Exception as e:
				# Contingency dump when the socket is not ready
				print(msg.decode("utf-8"), file=sys.stderr)
				print(
					"Error when writing to syslog '{}': {}".format(self._address, e),
					traceback.format_exc(),
					sep="\n",
					file=sys.stderr
				)

	def _on_read(self):
		try:
			_ = self._socket.recvfrom(1024)
			# We receive "something" ... let's ignore that!
			return
		except Exception as e:
			print("Error on the syslog socket '{}'".format(self._address), e, file=sys.stderr)


	def emit(self, record):
		"""
		This is the entry point for log entries.
		"""
		try:
			msg = self.format(record).encode('utf-8')

			if self._write_ready:
				try:
					self._socket.sendall(msg)
				except Exception as e:
					print("Error when writing to syslog '{}'".format(self._address), e, file=sys.stderr)
					self._enqueue(msg)

			else:
				self._enqueue(msg)


		except Exception as e:
			print("Error when emit to syslog '{}'".format(self._address), e, file=sys.stderr)
			self.handleError(record)


	def _enqueue(self, record):
		self._queue.put(record)


_RESET_SEQ = "\033[0m"
_COLOR_SEQ = "\033[1;%dm"
_BOLD_SEQ = "\033[1m"
