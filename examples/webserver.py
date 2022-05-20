#!/usr/bin/env python3
import asab
import aiohttp


class MyApplication(asab.Application):

	'''
	Run by:
	$ PYTHONPATH=.. ./webserver.py
	
	The application will be available at http://localhost:8080/
	'''

	async def initialize(self):
		# Loading the web service module
		from asab.web import Module
		self.add_module(Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a container
		container = asab.web.WebContainer(websvc, 'example:web', config={"listen": "0.0.0.0:8080"})

		# Add a route to the handler
		container.WebApp.router.add_get('/', self.hello)
		print("Test with curl:\n\t$ curl http://localhost:8080/")


	# This is the web request handler
	async def hello(self, request):
		return aiohttp.web.Response(text="Hello, world!\n")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
