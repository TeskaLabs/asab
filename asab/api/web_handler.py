import os
import asab
import asab.web
import aiohttp.web


class APIWebHandler(object):
	def __init__(self, app, webapp, log_handler):
		self.App = app

		# Add routes
		webapp.router.add_get("/asab/v1/environ", self.environ)
		webapp.router.add_get("/asab/v1/config", self.config)

		webapp.router.add_get("/asab/v1/logs", log_handler.get_logs)
		webapp.router.add_get("/asab/v1/logws", log_handler.ws)

		webapp.router.add_get("/asab/v1/changelog", self.changelog)

		if "asab:metrics:prometheus" in asab.Config.sections():
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
		path = asab.Config.get("general", "changelog_path")
		if not os.path.isfile(path):
			if os.path.isfile("/CHANGELOG.md"):
				path = "/CHANGELOG.md"
			elif os.path.isfile("CHANGELOG.md"):
				path = "CHANGELOG.md"
			else:
				return aiohttp.web.HTTPNotFound()

		with open(path) as f:
			result = f.read()

		return aiohttp.web.Response(text=result, content_type="text/markdown")

	async def environ(self, request):
		return asab.web.rest.json_response(request, dict(os.environ))

	async def config(self, request):
		# Copy the config and erase all passwords
		result = {}
		for section in asab.Config.sections():
			result[section] = {}
			# Access items in the raw mode (they are not interpolated)
			for option, value in asab.Config.items(section, raw=True):
				if section == "passwords":
					result[section][option] = "***"
				else:
					result[section][option] = value
		return asab.web.rest.json_response(request, result)
