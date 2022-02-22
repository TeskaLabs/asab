import aiohttp.web
import collections
import logging

L = logging.getLogger(__name__)


def metrics_middleware_factory(metrics_service):
	CounterTuple = collections.namedtuple("labels", ["method", "path", "status"])
	RequestCounter = metrics_service.create_counter(
		"web_requests",
		tags={
			"unit": "epm",
			"help": "Counts requests to asab endpoints.",
		},
	)

	@aiohttp.web.middleware
	async def metrics_middleware(request, handler):

		response = await handler(request)

		RequestCounter.add(
			CounterTuple(
				method=request.method, path=request.path, status=str(response.status)
			),
			1,
			init_value=0,
		)

		return response

	return metrics_middleware
