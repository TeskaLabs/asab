import aiohttp.web
import copy
import fnmatch
import datetime

from .openmetric import metric_to_openmetric
from ..web.rest import json_response
from ..web.auth import noauth
from ..web.tenant import allow_no_tenant


class MetricWebHandler(object):

	def __init__(self, metrics_svc, webapp):
		self.MetricsService = metrics_svc
		self.App = self.MetricsService.App

		# Add routes
		# TODO: Add access control (asab:service:access). Test with Prometheus first.
		webapp.router.add_get("/asab/v1/metrics", self.metrics)
		webapp.router.add_get("/asab/v1/watch_metrics", self.watch)
		webapp.router.add_get("/asab/v1/metrics.json", self.metrics_json)


	@noauth
	@allow_no_tenant
	async def metrics_json(self, request):
		'''
		Get metrics in a JSON.
		---
		tags: ['asab.metrics']
		'''
		metrics_to_send = copy.deepcopy(self.MetricsService.Storage.Metrics)
		return json_response(request, metrics_to_send)


	@noauth
	@allow_no_tenant
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


	@noauth
	@allow_no_tenant
	async def watch(self, request):
		"""
		Endpoint to list ASAB metrics in the command line.

		Example commands:
		* watch curl localhost:8080/asab/v1/watch_metrics -> all metrics

		Strict filters (inclusion and exclusion):
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=web_requests -> web_requests metric only
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=-web_requests -> all metrics w/o web_requests metric

		Includes only:
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=web* -> metrics that start with "web"
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=*web -> metrics that end with "web"
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=*web* -> metrics that contain "web"

		Excludes:
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=-web* -> metrics that start with "web"
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=-*web -> metrics that end with "web"
		* watch curl localhost:8080/asab/v1/watch_metrics?filter=-*web* -> metrics that contain "web"

		---
		tags: ['asab.metrics']
		"""

		filter = request.query.get("filter")
		tags = request.query.get("tags")
		tags = True if tags is not None and tags.lower() == 'true' else False
		text = watch_table(self.MetricsService.Storage.Metrics, filter, tags)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


def watch_table(metric_records: list, filter, tags):
	lines = []
	m_name_len = max([len(i["name"]) for i in metric_records])

	v_name_len = 0
	for i in metric_records:
		if len(i["fieldset"]) == 0:
			continue
		if len(i["fieldset"][0].get("values", {})) == 0:
			continue
		metric_name_len = max([len(str(value_name)) for value_name in i["fieldset"][0].get("values").keys()]) + 10
		if metric_name_len > v_name_len:
			v_name_len = metric_name_len

	timestamp_len = 30
	t_name_len = max([len(str(field["tags"])) for i in metric_records for field in i["fieldset"]])

	if tags:
		separator = "-" * (m_name_len + v_name_len + t_name_len + timestamp_len + 30 + 2)
	else:
		separator = "-" * (m_name_len + v_name_len + timestamp_len + 30 + 2)

	lines.append(separator)
	lines.append(build_line("Metric name", "Value name", "Value", "Timestamp", m_name_len, v_name_len, tags, timestamp_len, t_string="Tags", t_name_len=t_name_len))
	lines.append(separator)

	for metric_record in metric_records:
		for field in metric_record["fieldset"]:
			if field.get("values") is None:
				continue
			name = metric_record.get("name")
			timestamp = field.get("measured_at")
			timestamp = datetime.datetime.fromtimestamp(timestamp)

			if filter is not None:
				if filter.startswith("-"):
					if fnmatch.fnmatch(name, filter[1:]):
						continue
				else:
					if not fnmatch.fnmatch(name, filter):
						continue

			if metric_record.get("type") in ["Histogram", "HistogramWithDynamicTags"]:
				for upperboud, values in field.get("values").get("buckets").items():
					for v_name, value in values.items():
						lines.append(build_line(str(name), str(v_name), str(value), str(timestamp), m_name_len, v_name_len, tags, timestamp_len, str(upperboud), t_string=str(field["tags"]), t_name_len=t_name_len))

				lines.append(build_line(str(name), "Sum", field.get("values").get("sum"), str(timestamp), m_name_len, v_name_len, tags, timestamp_len, t_string=str(field["tags"]), t_name_len=t_name_len))
				lines.append(build_line(str(name), "Count", field.get("values").get("count"), str(timestamp), m_name_len, v_name_len, tags, timestamp_len, t_string=str(field["tags"]), t_name_len=t_name_len))

			else:
				for key, value in field.get("values").items():
					lines.append(build_line(str(name), str(key), str(value), str(timestamp), m_name_len, v_name_len, tags, timestamp_len, t_string=str(field["tags"]), t_name_len=t_name_len))

	text = "\n".join(lines)
	return text


def build_line(name, value_name, value, timestamp, m_name_len, v_name_len, tags, timestamp_len, upperbound=None, t_string=None, t_name_len=None):
	if upperbound is not None:
		if tags:
			line = (
				"{:<{m_name_len}} | {:<{t_name_len}} | {:<{v_name_len}} | {:<7} | {:<25} | {:<{timestamp_len}}".format(
					name,
					t_string,
					value_name,
					upperbound,
					value,
					timestamp,
					v_name_len=v_name_len - 10,
					m_name_len=m_name_len,
					t_name_len=t_name_len,
					timestamp_len=timestamp_len
				)
			)
		else:
			line = (
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<7} | {:<25} | {:<{timestamp_len}}".format(
					name,
					value_name,
					upperbound,
					value,
					timestamp,
					v_name_len=v_name_len - 10,
					m_name_len=m_name_len,
					timestamp_len=timestamp_len
				)
			)
	else:
		if tags:
			line = (
				"{:<{m_name_len}} | {:<{t_name_len}} | {:<{v_name_len}} | {:<25} | {:<{timestamp_len}}".format(
					name,
					t_string,
					value_name,
					value,
					timestamp,
					v_name_len=v_name_len,
					m_name_len=m_name_len,
					t_name_len=t_name_len,
					timestamp_len=timestamp_len
				)
			)
		else:
			line = (
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<25} | {:<{timestamp_len}}".format(
					name,
					value_name,
					value,
					timestamp,
					v_name_len=v_name_len,
					m_name_len=m_name_len,
					timestamp_len=timestamp_len
				)
			)

	return line
