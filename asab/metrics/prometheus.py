import asab


class PrometheusTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name, config)
		self.mlist = None

	async def process(self, now, mlist):
		self.now = now
		self.mlist = mlist

	def get_open_metric(self):
		if self.mlist:
			lines = []
			for metric, values in self.mlist:
				kwargs = {"values": values}
				record = metric.get_open_metric(**kwargs)
				if record:
					lines.append(record)
			lines.append("# EOF\n")
			text = '\n'.join(lines)
			return text
