class Storage(object):

	def __init__(self):
		self.Metrics = []


	def add(self, metric_name: str, metric_tags: dict):
		'''
		IMPORTANT: Add all metrics during init time, avoid adding metrics in runtime.
		'''

		for m in self.Metrics:
			if metric_name != m.get('name'):
				continue
			if metric_tags != m.get('tags'):
				continue
			raise RuntimeError("Metric '{}' / '{}' already exists in the storage".format(metric_name, metric_tags))


		metric = dict()
		metric['name'] = metric_name
		metric['tags'] = metric_tags
		metric['values'] = dict()
		metric['metadata'] = dict()

		self.Metrics.append(metric)
		return metric


	def values(self):
		return self.Metrics
