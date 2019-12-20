import logging
import datetime
import os
import sys
import platform
import json

from ..log import LOG_NOTICE


class LogmanIOLogHandler(logging.Handler):

	def __init__(self, svc, level=logging.NOTSET):
		super().__init__(level=level)

		self.Service = svc

		self.Facility = None  # TODO: Read this from config
		self.Pid = os.getpid()
		self.Environment = None
		self.Hostname = platform.node()
		self.Program = os.path.basename(sys.argv[0])


	def emit(self, record):
		if record.name == 'asab.metrics.service' and record.levelno == LOG_NOTICE:
			return  # No metrics to be submitted this way

		if record.levelno > logging.DEBUG and record.levelno <= logging.INFO:
			severity = 6  # Informational
		elif record.levelno <= LOG_NOTICE:
			severity = 5  # Notice
		elif record.levelno <= logging.WARNING:
			severity = 4  # Warning
		elif record.levelno <= logging.ERROR:
			severity = 3  # Error
		elif record.levelno <= logging.CRITICAL:
			severity = 2  # Critical
		else:
			severity = 1  # Alert

		log_entry = {
			"@timestamp": datetime.datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
			"T": "syslog",
			"H": self.Hostname,
			"P": self.Program,
			"C": record.name,
			"s": "{}:{}".format(record.funcName, record.lineno),
			"p": record.process,
			"Th": record.thread,
			"l": severity,
		}

		message = record.getMessage()
		if record.exc_text is not None:
			message += '\n' + record.exc_text
		if record.stack_info is not None:
			message += '\n' + record.stack_info
		if len(message) > 0:
			log_entry['M'] = message

		if self.Facility is not None:
			log_entry['f'] = self.Facility

		if self.Environment is not None:
			log_entry['e'] = self.Environment

		sd = record.__dict__.get("_struct_data")
		if sd is not None:
			log_entry['sd'] = sd

		self.Service.OutboundQueue.put_nowait(('sj', json.dumps(log_entry)))
