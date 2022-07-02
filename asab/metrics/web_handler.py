import aiohttp.web
import copy

from .openmetric import metric_to_openmetric
from ..web.rest import json_response


class MetricWebHandler(object):

	def __init__(self, metrics_svc, webapp):
		self.MetricsService = metrics_svc
		self.App = self.MetricsService.App

		# Add routes
		webapp.router.add_get("/asab/v1/metrics", self.metrics)
		webapp.router.add_get("/asab/v1/watch_metrics", self.watch)
		webapp.router.add_get("/asab/v1/metrics.json", self.metrics_json)


	async def metrics_json(self, request):
		'''
		Get metrics in a JSON.
		---
		tags: ['asab.metrics']
		'''
		metrics_to_send = copy.deepcopy(self.MetricsService.Storage.Metrics)
		for metrics in metrics_to_send:
			if metrics.get("@timestamp") is None:
				metrics["@timestamp"] = self.App.time()
		return json_response(request, metrics_to_send)


	async def metrics(self, request):
		'''
		Produce the OpenMetrics output.
		---
		tags: ['asab.metrics']
		'''
		lines = []

		for data in self.MetricsService.Storage.Metrics:
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
		"""
		Endpoint to list ASAB metrics in the command line.

		Example commands:
		* watch curl localhost:8080/asab/v1/metrics_watch
		* watch curl localhost:8080/asab/v1/metrics_watch?name=web_requests_duration_max

		---
		tags: ['asab.metrics']
		"""

		filter = request.query.get("name")
		tags = request.query.get("tags")
		text = watch_table(self.MetricsService.Storage.Metrics, filter, tags)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


def watch_table(metric_records: list(), filter, tags):
	lines = []
	m_name_len = max([len(i["name"]) for i in metric_records])
	v_name_len = max(
		[
			len(str(value_name))
			for i in metric_records
			if i["fieldset"][0].get("values") is not None
			for value_name in i["fieldset"][0].get("values").keys()
		]
	) + 10

	t_name_len = max([len(str(field["tags"])) for i in metric_records for field in i["fieldset"]])

	if tags:
		separator = "-" * (m_name_len + v_name_len + t_name_len + 30 + 2)
	else:
		separator = "-" * (m_name_len + v_name_len + 30 + 2)

	lines.append(separator)
	lines.append(build_line("Metric name", "Value name", "Value", m_name_len, v_name_len, tags, t_string="Tags", t_name_len=t_name_len))
	lines.append(separator)

	for metric_record in metric_records:
		for field in metric_record["fieldset"]:
			if field.get("values") is None:
				continue
			name = metric_record.get("name")
			if filter is not None and not name.startswith(filter):
				continue
			if metric_record.get("type") in ["Histogram", "HistogramWithDynamicTags"]:
				for upperboud, values in field.get("values").get("buckets").items():
					for v_name, value in values.items():
						lines.append(build_line(str(name), str(v_name), str(value), m_name_len, v_name_len, tags, str(upperboud), t_string=str(field["tags"]), t_name_len=t_name_len))

				lines.append(build_line(str(name), "Sum", field.get("values").get("sum"), m_name_len, v_name_len, tags, t_string=str(field["tags"]), t_name_len=t_name_len))
				lines.append(build_line(str(name), "Count", field.get("values").get("count"), m_name_len, v_name_len, tags, t_string=str(field["tags"]), t_name_len=t_name_len))

			else:
				for key, value in field.get("values").items():
					lines.append(build_line(str(name), str(key), str(value), m_name_len, v_name_len, tags, t_string=str(field["tags"]), t_name_len=t_name_len))

	text = "\n".join(lines)
	return text


def build_line(name, value_name, value, m_name_len, v_name_len, tags, upperbound=None, t_string=None, t_name_len=None):
	if upperbound is not None:
		if tags:
			line = (
				"{:<{m_name_len}} | {:<{t_name_len}} | {:<{v_name_len}} | {:<7} | {:<30}".format(
					name,
					t_string,
					value_name,
					upperbound,
					value,
					v_name_len=v_name_len - 10,
					m_name_len=m_name_len,
					t_name_len=t_name_len,
				)
			)
		else:
			line = (
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<7} | {:<30}".format(
					name,
					value_name,
					upperbound,
					value,
					v_name_len=v_name_len - 10,
					m_name_len=m_name_len,
				)
			)
	else:
		if tags:
			line = (
				"{:<{m_name_len}} | {:<{t_name_len}} | {:<{v_name_len}} | {:<30}".format(
					name,
					t_string,
					value_name,
					value,
					v_name_len=v_name_len,
					m_name_len=m_name_len,
					t_name_len=t_name_len,
				)
			)
		else:
			line = (
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
					name,
					value_name,
					value,
					v_name_len=v_name_len,
					m_name_len=m_name_len,
				)
			)

	return line
