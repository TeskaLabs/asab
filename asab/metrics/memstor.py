import asab

class MetricsMemstorTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		self.Values = {}

	async def process(self, now, mlist):
		for metric, values in mlist:
			self.Values[metric.Name] = values
