import os
import sys
import traceback
import time
import socket
import datetime
import pprint
import socket
import queue
import urllib.parse
import logging
import logging.handlers

import asyncio

from .config import Config

# Non-error/warning type of message that is visible without -v flag
LOG_NOTICE = 25 
logging.addLevelName(LOG_NOTICE, "NOTICE")

class Logging(object):

	def __init__(self, app):
		self.RootLogger = logging.getLogger()

		self.ConsoleHandler = None
		self.FileHandler = None
		self.SyslogHandler = None

		if not self.RootLogger.hasHandlers():
			
			# Add console logger
			# Don't initialize this when not on console
			if os.isatty(sys.stdin.fileno()):
				self.ConsoleHandler = logging.StreamHandler(stream=sys.stderr)
				self.ConsoleHandler.setFormatter(StructuredDataFormatter(
					fmt = Config["logging:console"]["format"],
					datefmt = Config["logging:console"]["datefmt"],
					sd_id = Config["logging"]["sd_id"],
				))
				self.ConsoleHandler.setLevel(logging.DEBUG)
				self.RootLogger.addHandler(self.ConsoleHandler)

			# Initialize file handler
			file_path = Config["logging:file"]["path"]

			if len(file_path) > 0:

				self.FileHandler = logging.handlers.RotatingFileHandler(
					file_path,
					backupCount = Config.getint("logging:file", "backup_count"),
				)
				self.FileHandler.setLevel(logging.DEBUG)
				self.FileHandler.setFormatter(StructuredDataFormatter(
					fmt = Config["logging:file"]["format"],
					datefmt = Config["logging:file"]["datefmt"],
					sd_id = Config["logging"]["sd_id"],
				))
				self.RootLogger.addHandler(self.FileHandler)

			# Initialize syslog
			if Config["logging:syslog"].getboolean("enabled"):

				address = Config["logging:syslog"]["address"]
				h = None

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
						self.SyslogHandler = AsyncIOHandler(app.Loop, socket.AF_INET, socket.SOCK_DGRAM, (
							url.hostname if url.hostname is not None else 'localhost',
							url.port if url.port is not None else logging.handlers.SYSLOG_UDP_PORT
						))

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
						self.SyslogHandler.setFormatter(MacOSXSyslogFormatter(sd_id = Config["logging"]["sd_id"]))
					elif format == '5':
						self.SyslogHandler.setFormatter(SyslogRFC5424Formatter(sd_id = Config["logging"]["sd_id"]))
					else:
						self.SyslogHandler.setFormatter(SyslogRFC3164Formatter(sd_id = Config["logging"]["sd_id"]))
					self.RootLogger.addHandler(self.SyslogHandler)

		else:
			self.RootLogger.warning("Logging seems to be already configured. Proceed with caution.")

		if Config["logging"].getboolean("verbose"):
			self.RootLogger.setLevel(logging.DEBUG)
		else:
			self.RootLogger.setLevel(LOG_NOTICE)


	def rotate(self):
		if self.FileHandler is not None:
			self.RootLogger.info("Rotating logs")
			self.FileHandler.doRollover()

###

class _StructuredDataLogger(logging.Logger):
	'''
This class extends a default python logger class, specifically by adding ``struct_data`` parameter to logging functions.
It means that you can use expressions such as ``logger.info("Hello world!", struct_data={'key':'value'})``.
	'''

	def _log(self, level, msg, args, exc_info=None, struct_data=None, extra=None, stack_info=False):
		if struct_data is not None:
			if extra is None: extra = dict()
			extra['_struct_data'] = struct_data

		super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)


logging.setLoggerClass(_StructuredDataLogger)

###

class StructuredDataFormatter(logging.Formatter):
	'''
	The logging formatter that renders log messages that includes structured data.
	'''

	empty_sd = ""

	def __init__(self, facility=16, fmt=None, datefmt=None, style='%', sd_id='sd'):
		super().__init__(fmt, datefmt, style)
		self.SD_id = sd_id
		self.Facility = facility


	def format(self, record):
		'''
		Format the specified record as text.
		'''

		record.struct_data=self.render_struct_data(record.__dict__.get("_struct_data"))
		
		# The Priority value is calculated by first multiplying the Facility number by 8 and then adding the numerical value of the Severity.
		severity = 7 # Debug
		if record.levelno > logging.DEBUG and record.levelno <= logging.INFO:
			severity = 6 # Informational
		elif record.levelno <= LOG_NOTICE:
			severity = 5 # Notice
		elif record.levelno <= logging.WARNING:
			severity = 4 # Warning
		elif record.levelno <= logging.ERROR:
			severity = 3 # Error
		elif record.levelno <= logging.CRITICAL:
			severity = 2 # Critical
		else:
			severity = 1 # Alert

		record.priority = (self.Facility << 3) + severity
		return super().format(record)


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
		tb_lines = [ line.rstrip('\n') for line in traceback.format_exception(exception.__class__, exception, ex_traceback)]
		message += '\n' + '\n'.join(tb_lines)

	logging.getLogger().error(message)

##

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

##

class SyslogRFC3164Formatter(StructuredDataFormatter):
	""" 
	It implements Syslog formatting for Mac OSX syslog (aka format ``3``).
	"""

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id='sd'):
		fmt = '<%(priority)s>%(asctime)s {app_name} {proc_id} %(levelname)s %(name)s %(struct_data)s%(message)s\000'.format(
			app_name=Config["logging"]["app_name"],
			hostname=socket.gethostname(),
			proc_id=os.getpid(),
		)

		# Initialize formatter
		super().__init__(fmt=fmt, datefmt='%b %d %H:%M:%S', style=style, sd_id=sd_id)

##

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


class AsyncIOHandler(logging.Handler):

	'''
A logging handler similar to a standard ``logging.handlers.SocketHandler`` that utilizes ``asyncio``.
It implements a queue for decoupling logging from a networking. The networking is fully event-driven via ``asyncio`` mechanisms.
	'''

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
			self._loop.remove_writer(self._socket, self._on_write)
			self._loop.remove_reader(self._socket, self._on_read)
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
			# TODO: Handle eventual error in writing -> break the cycle and restart on write handler
			msg = self._queue.get_nowait()
			self._socket.sendall(msg)


	def _on_read(self):
		# Close a socket - there is no reason for reading or socket is actually closed
		self._reset()


	def emit(self, record):
		'''
		This is the entry point for log entries.
		'''
		try:
			msg = self.format(record).encode('utf-8')

			if self._write_ready:
				try:
					self._socket.sendall(msg)
				except Exception as e:
					print("Error when writing to syslog '{}'".format(self._address), e, file=sys.stderr)
					self._enqueue(msg)

			else:
				self._enqueue(record)


		except Exception as e:
			print("Error when emit to syslog '{}'".format(self._address), e, file=sys.stderr)
			self.handleError(record)


	def _enqueue(self, record):
		self._queue.put(record)
