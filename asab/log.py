import os
import logging
import logging.handlers
import time
import socket



class StructuredDataLogger(logging.Logger):
	def _log(self, level, msg, args, exc_info=None, struct_data=None, extra=None, stack_info=False):
		if struct_data is not None:
			if extra is None: extra = dict()
			extra['_struct_data'] = struct_data
		super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)



class RFC5424Formatter(logging.Formatter):
	""" This formatter is meant for a SysLogHandler """

	def __init__(self, app_name='-', sd_id="L"):
		self.sd_id = sd_id

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


	def format(self, record):
		record.struct_data=self.render_struct_data(record.__dict__.get("_struct_data"))
		return super().format(record)


	def render_struct_data(self, struct_data):
		if struct_data is None:
			return ""
		else:
			return "[{sd_id} {sd_params}]".format(
				sd_id=self.sd_id,
				sd_params=" ".join(['{}="{}"'.format(key, val) for key, val in struct_data.items()]))



if __name__ == '__main__':
	logging.setLoggerClass(StructuredDataLogger)
	handler = logging.handlers.SysLogHandler()
	handler.setFormatter(RFC5424Formatter())
	handler.setLevel(logging.INFO)
	L = logging.getLogger(__name__)
	L.setLevel(logging.INFO)
	L.addHandler(handler)

	L.info("Info message with structured data", struct_data={"sd1": "test"})
	L.warn("Warn message, with structured data", struct_data={"sd1": "test", "sd2": "test2"})
	L.error("Error message without structured data")
