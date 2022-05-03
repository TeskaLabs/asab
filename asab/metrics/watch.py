

class WatchTarget(object):
	def __init__(self, svc):
		super().__init__()
		self.MetricsService = svc

	def watch_table(self, request):
		"""
		Pull model target to list ASAB metrics in the command line.
		Example commands:
		watch curl localhost:8080/asab/v1/metrics_watch
		watch curl localhost:8080/asab/v1/metrics_watch?name=web_requests_duration_max
		"""
		filter = request.query.get("name")

		metric_records = list()
		for metric_name, metric in self.MetricsService.Metrics.items():
			try:
				metric_record = metric_records.append(metric.LastRecord)
			except AttributeError:
				metric_record = metric_records.append(metric.rest_get())

		lines = []
		m_name_len = max([len(metric_record.get("Name")) for metric_record in metric_records])
		v_name_len = max(
			[
				len(str(value.get("value_name")))
				for i in metric_records
				for value in i.get("Values")
			]
		)

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

		for metric_record in metric_records:
			name = metric_record.get("Name")
			if filter is not None and not name.startswith(filter):
				continue
			for i in metric_record.get("Values"):
				lines.append(
					"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
						str(name),
						str(i.get("value_name")),
						str(i.get("value")),
						v_name_len=v_name_len,
						m_name_len=m_name_len,
					)
				)

		text = "\n".join(lines)
		return text
