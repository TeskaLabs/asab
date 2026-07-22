import logging
from ..abc import Service
from ..log import LOG_NOTICE

#

L = logging.getLogger(__name__)

#


class NativeMetrics(Service):
	'''
	This service is responsible for reading native metrics.
	There are:
	* memory metrics
	'''


	def __init__(self, app, metrics_svc):
		self.MemoryGauge = metrics_svc.create_gauge("memory")
		self._MemoryMetricsAvailable = True

		# Injecting logging metrics into MetricsHandler and MetricsHandler into Root Logger
		self.MetricsLoggingHandler = MetricsLoggingHandler()
		self.MetricsLoggingHandler.LogCounter = metrics_svc.create_counter("logs", init_values={"warnings": 0, "errors": 0, "critical": 0}, help="Counts WARNING, ERROR and CRITICAL logs per minute.")
		logging.root.addHandler(self.MetricsLoggingHandler)

		app.PubSub.subscribe("Metrics.flush!", self._on_flushing_event)
		self._on_flushing_event()


	def _on_flushing_event(self, event_name=None):
		if not self._MemoryMetricsAvailable:
			return

		try:
			with open("/proc/self/status", "r") as file:
				proc_status = file.read()

				for proc_status_line in proc_status.replace('\t', '').split('\n'):

					# Vm - virtual memory, other metrics need to be evaluated and added
					if proc_status_line.startswith("Vm"):
						proc_status_info = proc_status_line.split(' ')
						try:
							self.MemoryGauge.set(proc_status_info[0][:-1], int(proc_status_info[-2]) * 1024)
						except ValueError:
							pass

		except FileNotFoundError:
			# Typical on non-Linux platforms; log once to avoid spam on every flush.
			self._MemoryMetricsAvailable = False
			L.warning(
				"Native memory metrics are unavailable because '/proc/self/status' was not found; skipping memory gauge updates.",
				struct_data={"path": "/proc/self/status"},
			)


class MetricsLoggingHandler(logging.Handler):

	def emit(self, record):
		level = record.levelno
		if level <= LOG_NOTICE:
			return
		elif level <= logging.WARNING:
			self.LogCounter.add("warnings", 1)
		elif level <= logging.ERROR:
			self.LogCounter.add("errors", 1)
		elif level <= logging.CRITICAL:
			self.LogCounter.add("critical", 1)
