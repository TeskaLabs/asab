#!/usr/bin/env python3
import aiohttp.web

import asab
import asab.web

from jsonrpcserver.aio import methods


@methods.add
async def ping():
	return 'pong'


class MyApplication(asab.Application):


	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Enable exception to JSON exception middleware
		websvc.WebApp.middlewares.append(asab.web.JsonExceptionMiddleware)

		# Add a route
		websvc.WebApp.router.add_post('/rpc', self.rpc)


	async def rpc(self, request):
		request = await request.text()
		response = await methods.dispatch(request)
		if response.is_notification:
			return aiohttp.web.Response()
		else:
			return aiohttp.web.json_response(response, status=response.http_status)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
