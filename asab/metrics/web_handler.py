import aiohttp.web


class MetricWebHandler(object):

	def __init__(self, metrics_svc, webapp):
		self.MetricsService = metrics_svc

		# Add routes
		webapp.router.add_get("/asab/v1/metrics", self.metrics)
		webapp.router.add_get("/asab/v1/watch_metrics", self.watch)


	async def metrics(self, request):
		text = self.MetricsService.MetricsDataStorage.get_all_in_openmetric()
		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)

	async def watch(self, request):
		filter = request.query.get("name")
		text = self.MetricsService.MetricsDataStorage.get_all_as_table(filter)

		return aiohttp.web.Response(
			text=text,
			content_type="text/plain",
			charset="utf-8",
		)
