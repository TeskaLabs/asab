import aiohttp.web
import collections


def metrics_middleware_factory(metrics_service):
	CounterTuple = collections.namedtuple("labels", ["method", "path", "status"])
	ResponseCounter = metrics_service.create_counter(
		"web_requests",
		tags={
			"unit": "requests_per_minute",
			"help": "Counts requests to asab endpoints.",
		},
	)


	@aiohttp.web.middleware
	async def metrics_middleware(request, handler):

		response = await handler(request)

		ResponseCounter.add(
			CounterTuple(method=request.method, path=request.path, status=str(response.status)), 1, init_value=0,)

		return response

	return metrics_middleware
