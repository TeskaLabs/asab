class Storage(object):

	def __init__(self):
		self.Metrics = []


	def add(self, metric_name: str, tags: dict, reset: bool, help: str, unit: str):
		'''
		IMPORTANT: Add all metrics during init time, avoid adding metrics in runtime.
		'''

		for m in self.Metrics:
			if metric_name != m.get('name'):
				continue
			if tags != m.get("tags"):
				continue
			raise RuntimeError("Metric '{}/{}' already exists in the storage".format(metric_name, tags))

		metric = dict()
		metric['type'] = None  # Will be filled a bit later
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
