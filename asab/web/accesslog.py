import aiohttp.abc

from ..log import LOG_NOTICE


class AccessLogger(aiohttp.abc.AbstractAccessLogger):

	def __init__(self, logger, log_format) -> None:
		super().__init__(logger, log_format)
		self.App = logger.App
		self.WebService = self.App.get_service("asab.WebService")

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
		path = request.match_info.get_info().get("formatter")
		if path is None:
			path = request.path

		self.WebService.WebRequestsMetrics.set_metrics(time, request.method, path, str(response.status))
