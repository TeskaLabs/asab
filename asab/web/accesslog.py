import collections

import aiohttp.abc

from ..log import LOG_NOTICE


class AccessLogger(aiohttp.abc.AbstractAccessLogger):

	def __init__(self, logger, log_format) -> None:
		super().__init__(logger, log_format)
		self.App = logger.App
		metrics_service = self.App.get_service("asab.MetricsService")
		self.MetricNameTuple = collections.namedtuple("labels", ["method", "path", "status"])

		self.MaxDurationCounter = metrics_service.create_extreme_counter(
			"web_requests_duration_max",
			tags={"help": "Counts maximum request duration to asab endpoints per minute."}
		)

		self.MinDurationCounter = metrics_service.create_extreme_counter(
			"web_requests_duration_min",
			tags={"help": "Counts minimal request duration to asab endpoints per minute."},
			extreme="min"
		)

		self.RequestCounter = metrics_service.create_counter(
			"web_requests",
			tags={
				"unit": "epm",
				"help": "Counts requests to asab endpoints as events per minute.",
			},
		)

		self.DurationCounter = metrics_service.create_counter(
			"web_requests_duration",
			tags={
				"unit": "seconds_per_minute",
				"help": "Counts total requests duration to asab endpoints per minute.",
			},
		)

	def log(self, request, response, time):
		struct_data = {
			'I': request.remote,
			'al.m': request.method,
			'al.p': request.path,
			'al.c': response.status,
			'D': time,
		}

		if request.content_length is not None:
			struct_data['al.B'] = request.content_length

		if response.content_length is not None:
			struct_data['al.b'] = response.content_length

		if hasattr(request, 'Identity'):
			struct_data['i'] = request.Identity

		agent = request.headers.get('User-Agent')
		if agent is not None:
			struct_data['al.A'] = agent

		xfwd = request.headers.get('X-Forwarded-For')
		if xfwd is not None:
			# TODO: Sanitize xfwd
			# In nginx, use "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
			struct_data['Ix'] = xfwd[:128]

		self.logger.log(LOG_NOTICE, '', struct_data=struct_data)

		# Metrics
		value_name = self.MetricNameTuple(method=request.method, path=request.path, status=str(response.status))

		# max
		self.MaxDurationCounter.set(value_name, time, init_value=0)

		# min
		self.MinDurationCounter.set(value_name, time, init_value=1000)

		# count
		self.RequestCounter.add(value_name, 1, init_value=0)

		# total duration
		self.DurationCounter.add(value_name, time, init_value=0)

		print("-----------------------------")
		print(self.MaxDurationCounter.rest_get())
		print(self.MinDurationCounter.rest_get())
		print(self.RequestCounter.rest_get())
		print(self.DurationCounter.rest_get())
