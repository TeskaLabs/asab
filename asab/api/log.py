import logging
import datetime

from ..web.rest.json import json_response
from ..log import LOG_NOTICE

##

L = logging.getLogger(__name__)


##


class WebApiLoggingHandler(logging.Handler):

	def __init__(self, level=logging.NOTSET, buffer_size: int = 10):
		super().__init__(level=level)

		self.buffer = []
		self._buffer_size = buffer_size

	def emit(self, record):
		if logging.DEBUG < record.levelno <= logging.INFO:
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

		sd = record.__dict__.get("_struct_data")
		if sd is not None:
			log_entry['sd'] = sd

		if len(self.buffer) > self._buffer_size:
			del self.buffer[0]
			self.buffer.append(log_entry)

		else:
			self.buffer.append(log_entry)

	async def logs(self, request):
		return json_response(request, self.buffer)
