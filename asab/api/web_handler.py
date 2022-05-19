import os

import aiohttp.web

from .. import Config
from ..web.rest import json_response


class APIWebHandler(object):

	def __init__(self, api_svc, webapp, log_handler):
		self.App = api_svc.App
		self.ApiService = api_svc

		# Add routes
		webapp.router.add_get("/asab/v1/environ", self.environ)
		webapp.router.add_get("/asab/v1/config", self.config)

		webapp.router.add_get("/asab/v1/logs", log_handler.get_logs)
		webapp.router.add_get("/asab/v1/logws", log_handler.ws)

		webapp.router.add_get("/asab/v1/changelog", self.changelog)
		webapp.router.add_get("/asab/v1/manifest", self.manifest)

		if "asab:metrics:prometheus" in Config.sections():
			self.MetricsService = self.App.get_service("asab.MetricsService")
			if self.MetricsService is None:
				raise RuntimeError("asab.MetricsService is not available")
			if self.MetricsService.PrometheusTarget is not None:
				webapp.router.add_get("/asab/v1/metrics", self.metrics)
				webapp.router.add_get("/asab/v1/metrics/watch", self.watch)


	async def metrics(self, request):
		text = self.MetricsService.PrometheusTarget.get_open_metric()

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


	async def watch(self, request):
		text = self.MetricsService.PrometheusTarget.watch_table(request)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)


	async def changelog(self, request):
		if self.ApiService.ChangeLog is None:
			return aiohttp.web.HTTPNotFound()

		with open(self.ApiService.ChangeLog, 'r') as f:
			result = f.read()

		return aiohttp.web.Response(text=result, content_type="text/markdown")


	async def manifest(self, request):
		if self.ApiService.Manifest is None:
			return aiohttp.web.HTTPNotFound()

		return json_response(request, self.ApiService.Manifest)


	async def environ(self, request):
		return json_response(request, dict(os.environ))


	async def config(self, request):
		# Copy the config and erase all passwords
		result = {}
		for section in Config.sections():
			result[section] = {}
			# Access items in the raw mode (they are not interpolated)
			for option, value in Config.items(section, raw=True):
				if section == "passwords":
					result[section][option] = "***"
				else:
					result[section][option] = value
		return json_response(request, result)
