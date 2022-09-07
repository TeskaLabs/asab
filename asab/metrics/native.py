import logging
from ..abc import Service

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
		self.MemoryGauge = metrics_svc.create_gauge("os.stat")

		# injecting logging metrics into logging manager
		logging.root.manager.LogCounter = metrics_svc.create_counter("logs", dynamic_tags=True)

		app.PubSub.subscribe("Metrics.flush!", self._on_flushing_event)
		self._on_flushing_event()


	def _on_flushing_event(self, event_name=None):
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
			pass
			# L.warning("File '/proc/self/status' was not found, skipping reading native metrics.")
