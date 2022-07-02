#!/usr/bin/env python3
import asab
import asab.web

import aiohttp


class MyApplication(asab.Application):

	'''
	Run by:  
	`$ PYTHONPATH=.. ./webserver.py`
	
	The application will be available at http://localhost:8080/
	'''

	def __init__(self):
		# Loading the ASAB Web module
		super().__init__(modules=[asab.web.Module])

		# Locate the Web service
		websvc = self.get_service("asab.WebService")

		# Create the Web container
		container = asab.web.WebContainer(websvc, 'my:web', config={"listen": "0.0.0.0:8080"})

		# Add a route to the handler
		container.WebApp.router.add_get('/', self.hello)
		print("Test with curl:\n\t$ curl http://localhost:8080/")


	# This is the web request handler
	async def hello(self, request):
		return aiohttp.web.Response(text="Hello, world!\n")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
