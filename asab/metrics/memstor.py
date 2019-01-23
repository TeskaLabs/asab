import asab

class MetricsMemstorTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		self.Values = {}
		self.Tags = {}
		self.Timestamp = None

	async def process(self, now, mlist):
		self.Timestamp = now
		for metric, values in mlist:
			self.Tags[metric.Name] = metric.Tags
			self.Values[metric.Name] = values

	def rest_get(self):
		ret = {}
		for name, values in self.Values.items():
			ret[name] = {}
			ret[name]["Name"] = name
			ret[name]["Values"] = values
		for name, tags in self.Tags.items():
			if ret.get(name) is None:
				ret[name] = {}
				ret[name]["Name"] = name
			ret[name]["Tags"] = tags
			ret[name]["Timestamp"] = self.Timestamp

		return ret
