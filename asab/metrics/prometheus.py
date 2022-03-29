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

	def watch_table(self, request):
		agg = request.query.get("agg")
		lines = []
		if self.mlist:
			m_name_len = max([len(metric.Name) for metric, values in self.mlist])
			print(m_name_len)
				
			if agg == "sum":
				lines.append("-" * 60)
				lines.append("{:<{m_name_len}} {:<30}".format("Metric name", "Metric values SUM", m_name_len=m_name_len))
				lines.append("-" * 60)
				for metric, values in self.mlist:
					name = metric.Name
					_sum = sum(values.values())
					print(_sum)
					lines.append("{:<{m_name_len}} {:<30}".format(str(name), sum(values.values()), m_name_len=m_name_len))
			else:
				lines.append("-" * 90)
				lines.append("{:<30} {:<30} {:<30}".format("Metric name", "Value name", "Value"))
				lines.append("-" * 90)
				for metric, values in self.mlist:
					name = metric.Name
					for value_name, value in values.items():
						lines.append("{:<30} {:<30} {:<30}".format(str(name), str(value_name), str(value)))
		text = '\n'.join(lines)
		return text