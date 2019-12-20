import asab


class MetricsMemstorTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name, config)
		self.Metrics = {}


	async def process(self, now, mlist):

		for metric, values in mlist:
			# Build metric name with tags
			name = metric.Name
			for tk, tv in metric.Tags.items():
				name += ',{}={}'.format(tk, tv)
			# Store metric
			self.Metrics[name] = {
				"Timestamp": now,
				"Name": metric.Name,
				"Values": values,
				"Tags": metric.Tags
			}


	def rest_get(self):
		return self.Metrics
