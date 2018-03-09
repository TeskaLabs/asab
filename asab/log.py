import os
import sys
import logging
import logging.handlers
import traceback
import time
import datetime
import pprint
import socket
from .config import Config


def _setup_logging():

	root_logger = logging.getLogger()
	if not root_logger.hasHandlers():
		
		# Add console logger
		#TODO: Don't initialize this when not on console
		h = logging.StreamHandler(stream=sys.stderr)
		h.setFormatter(StructuredDataFormatter(
			fmt = Config["logging:console"]["format"],
			datefmt = Config["logging:console"]["datefmt"],
			sd_id = Config["logging:rfc5424"]["sd_id"],
		))
		h.setLevel(logging.DEBUG)
		root_logger.addHandler(h)

		#TODO: If configured, initialize syslog

	else:
		root_logger.warning("Logging seems to be already configured. Proceed with caution.")

	if Config["general"]["verbose"] == "True":
		root_logger.setLevel(logging.DEBUG)
	else:
		root_logger.setLevel(logging.WARNING)


class StructuredDataLogger(logging.Logger):

	def _log(self, level, msg, args, exc_info=None, struct_data=None, extra=None, stack_info=False):
		if struct_data is not None:
			if extra is None: extra = dict()
			extra['_struct_data'] = struct_data

		super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)

logging.setLoggerClass(StructuredDataLogger)


class StructuredDataFormatter(logging.Formatter):

	def __init__(self, fmt=None, datefmt=None, style='%', sd_id=None):
		super().__init__(fmt, datefmt, style)
		self.sd_id = sd_id

	def format(self, record):
		record.struct_data=self.render_struct_data(record.__dict__.get("_struct_data"))
		return super().format(record)


	def formatTime(self, record, datefmt=None):
		ct = datetime.datetime.fromtimestamp(record.created)
		if datefmt:
			s = ct.strftime(datefmt)
		else:
			t = ct.strftime("%Y-%m-%d %H:%M:%S")
			s = "%s.%03d" % (t, record.msecs)
		return s

	def render_struct_data(self, struct_data):
		if struct_data is None:
			return ""
		else:
			return "[{sd_id} {sd_params}]".format(
				sd_id=self.sd_id,
				sd_params=" ".join(['{}="{}"'.format(key, val) for key, val in struct_data.items()]))



class RFC5424Formatter(StructuredDataFormatter):
	""" This formatter is meant for a SysLogHandler """

	def __init__(self, fmt=None, datefmt=None, style='%'):
		super().__init__(fmt, datefmt, style)
		app_name=Config["logging:formatter_rfc5424"]["app_name"]

		# RFC5424 format
		fmt = '{header} {structured_data} {message}'.format(
			header='{version} {timestamp} {hostname} {app_name} {proc_id} {msg_id}'.format(
				version="1",
				timestamp='%(asctime)s.%(msecs)dZ',
				hostname=socket.gethostname(),
				app_name=app_name,
				proc_id=os.getpid(),
				msg_id='-'),
			structured_data='%(struct_data)s',
			message='%(message)s'
		)

		# Initialize formatter
		super().__init__(
			fmt=fmt,
			datefmt='%Y-%m-%dT%H:%M:%S',
			style='%')

		# Convert time to GMT
		self.converter = time.gmtime



def _loop_exception_handler(loop, context):
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



if __name__ == '__main__':
	handler = logging.handlers.SysLogHandler()
	handler.setFormatter(RFC5424Formatter())
	handler.setLevel(logging.INFO)
	L = logging.getLogger(__name__)
	L.setLevel(logging.INFO)
	L.addHandler(handler)

	L.info("Info message with structured data", struct_data={"sd1": "test"})
	L.warn("Warn message, with structured data", struct_data={"sd1": "test", "sd2": "test2"})
	L.error("Error message without structured data")
