import logging
import collections

#

L = logging.getLogger(__name__)

#


class Metrics(collections.MutableMapping):
	"""
	Manage scalar metrics of the application
	"""

	def __init__(self, app):
		self.metrics = {}

	def add(self, metric_name, value=1):
		""" Add a value to the specified metric. """

		if metric_name not in self.metrics:
			self.metrics[metric_name] = 0
		self.metrics[metric_name] += value

	def set(self, metric_name, value=0):
		""" Set a value of a specified metric. """

		self.metrics[metric_name] = value

	def keys(self):
		""" Get metric names as keys. """

		return self.metrics.keys()

	def __getitem__(self, key):
		if key not in self.metrics:
			return None
		return self.metrics.__getitem__(key)

	def __setitem__(self, key, value):
		return self.metrics.__setitem__(key, value)

	def __delitem__(self, key):
		if key not in self.metrics:
			return
		return self.metrics.__delitem__(key)

	def __iter__(self):
		return self.metrics.__iter__()

	def __len__(self):
		return self.metrics.__len__()
