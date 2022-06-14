import aiohttp.web

from .openmetric import metric_to_openmetric


class MetricWebHandler(object):

	def __init__(self, metrics_svc, webapp):
		self.MetricsService = metrics_svc

		# Add routes
		webapp.router.add_get("/asab/v1/metrics", self.metrics)
		webapp.router.add_get("/asab/v1/watch_metrics", self.watch)



	async def metrics(self, request):
		lines = []

		for data in self.MetricsService.Storage.values():
			line = metric_to_openmetric(data)
			if line is not None:
				lines.append(line)

		if lines:
			lines.append("# EOF\n")

		text = "\n".join(lines)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


	async def watch(self, request):
		filter = request.query.get("name")
		text = watch_table(self.MetricsService.Storage.values(), filter)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


def watch_table(metric_records: list(), filter):
	"""
	Endpoint to list ASAB metrics in the command line.
	Example commands:
	watch curl localhost:8080/asab/v1/metrics_watch
	watch curl localhost:8080/asab/v1/metrics_watch?name=web_requests_duration_max
	"""
	lines = []
	m_name_len = max([len(i.get("Name")) for i in metric_records])
	v_name_len = max(
		[
			len(str(value_name))
			for i in metric_records
			if i.get("Values") is not None
			for value_name in i.get("Values")
		]
	) + 10

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
		if metric_record.get("Values") is None:
			continue
		name = metric_record.get("Name")
		if filter is not None and not name.startswith(filter):
			continue
		if metric_record.get("Type") == "Histogram":
			for upperboud, values in metric_record.get("Values").get("Buckets").items():
				for v_name, value in values.items():
					lines.append(
						"{:<{m_name_len}} | {:<{v_name_len}} | {:<7} | {:<30}".format(
							str(name),
							str(v_name),
							str(upperboud),
							str(value),
							v_name_len=v_name_len - 10,
							m_name_len=m_name_len,
						)
					)
			lines.append(
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
					str(name),
					"Sum",
					metric_record.get("Values").get("Sum"),
					v_name_len=v_name_len,
					m_name_len=m_name_len,
				)
			)
			lines.append(
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
					str(name),
					"Count",
					metric_record.get("Values").get("Count"),
					v_name_len=v_name_len,
					m_name_len=m_name_len,
				)
			)

		else:
			for key, value in metric_record.get("Values").items():
				lines.append(
					"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
						str(name),
						str(key),
						str(value),
						v_name_len=v_name_len,
						m_name_len=m_name_len,
					)
				)

	text = "\n".join(lines)
	return text
