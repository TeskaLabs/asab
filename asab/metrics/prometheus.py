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
			text = "\n".join(lines)
			return text

	def watch_table(self, request):
		"""
		Extension of Prometheus Target to list ASAB metrics in the command line.
		Example commands:
		watch curl localhost:8080/asab/v1/metrics/watch
		watch curl localhost:8080/asab/v1/metrics/watch?agg=sum
		"""
		agg = request.query.get("agg")
		lines = []
		if self.mlist:
			m_name_len = max([len(metric.Name) for metric, values in self.mlist])
			v_name_len = max(
				[
					len(str(value_name))
					for metric, values in self.mlist
					for value_name in values.keys()
				]
			)

			if agg == "sum":
				separator = "-" * (m_name_len + 30 + 2)
				lines.append(separator)
				lines.append(
					"{:<{m_name_len}} | {:<30}".format(
						"Metric name", "Metric values SUM", m_name_len=m_name_len
					)
				)
				lines.append(separator)
				for metric, values in self.mlist:
					name = metric.Name
					lines.append(
						"{:<{m_name_len}} | {:<30}".format(
							str(name), sum(values.values()), m_name_len=m_name_len
						)
					)

			else:
				separator = "-" * (m_name_len + v_name_len + 30 + 2)
				lines.append(separator)
				lines.append(
					"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
						"Metric name",
						"Value name",
						"Value",
						v_name_len=v_name_len,
						m_name_len=m_name_len,
					)
				)
				lines.append(separator)
				for metric, values in self.mlist:
					name = metric.Name
					for value_name, value in values.items():
						lines.append(
							"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
								str(name),
								str(value_name),
								str(value),
								v_name_len=v_name_len,
								m_name_len=m_name_len,
							)
						)
		text = "\n".join(lines)
		return text
