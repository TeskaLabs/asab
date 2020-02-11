import logging
import datetime
from asab.log import LOG_NOTICE


class APIHandler(logging.Handler):

	def __init__(self, level=logging.NOTSET, storage=None):
		super().__init__(level=level)

		self.level = level
		self.buffer = storage

	def emit(self, record):
		if record.name == 'asab.metrics.service' and record.levelno == LOG_NOTICE:
			return  # No metrics to be submitted this way

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

		if len(self.buffer) > 10:
			del self.buffer[0]
			self.buffer.append(log_entry)

		else:
			self.buffer.append(log_entry)

		return self.buffer
