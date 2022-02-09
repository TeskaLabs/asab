import aiohttp.web



def metrics_middleware_factory(metrics_service):
	counters = {}

	@aiohttp.web.middleware
	async def metrics_middleware(request, handler):
		"""
		Add the application object to the request.
		"""
		request.path
		if request.path not in counters.keys():
			counters[request.path] = metrics_service.create_counter(request.path, tags={"help": "help", "unit": "requests", "default-label": "RequestMetrics"})
		
		print("before")

		response = await handler(request)

		muj_counter = counters[request.path]
		muj_counter.add("{}_{}".format(str(request.method), str(response.status)), 1, init_value=0)

		print("after")

		return response
	return metrics_middleware
