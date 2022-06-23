import logging

#

L = logging.getLogger(__name__)

#


class Storage(object):

	def __init__(self):
		self.Metrics = []


	def add(self, metric_name: str, tags: dict, reset: bool, help: str, unit: str):

		for i in range(len(self.Metrics) - 1, -1, -1):
			metric = self.Metrics[i]
			if metric_name != metric['name']:
				continue
			if tags != metric["static_tags"]:
				continue

			# There is existing storage for a metrics and we are going to overwrite it.
			# It means that the existing metrics will diapear from output and will be replaced by a new one.
			# It is designed to support e.g. dynamic prebuilds of the classes with the same metrics.
			# In other cases, this path should be avoided by e.g. creation of metrics in init time, not during runtime
			L.debug("The metrics storage '{}/{}' is overriden".format(metric_name, tags))
			del self.Metrics[i]

		metric = dict()
		metric['type'] = None  # Will be filled a bit later
		metric['static_tags'] = tags
		metric['name'] = metric_name
		metric['fieldset'] = list()

		if reset is not None:
			metric['reset'] = reset
		if help is not None:
			metric['help'] = help
		if unit is not None:
			metric['unit'] = unit

		self.Metrics.append(metric)
		return metric


	def clear(self):
		self.Metrics.clear()
