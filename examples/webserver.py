#!/usr/bin/env python3
import asab
import aiohttp

class MyApplication(asab.Application):

	async def initialize(self):
		# Loading the web service module
		from asab.web import Module
		self.add_module(Module)

		# Locate web service
		svc = self.get_service("asab.WebService")

		# Add a route
		svc.WebApp.router.add_get('/hello', self.hello)

		print("Test with curl:\n\t$ curl http://localhost:8080/hello")

	# Simplistic view
	async def hello(self, request):
		return aiohttp.web.Response(text='Hello!\n')

if __name__ == '__main__':
	app = MyApplication()
	app.run()
