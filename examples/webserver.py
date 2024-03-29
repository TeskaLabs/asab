#!/usr/bin/env python3

import asab.api
import asab.web.rest


class MyApplication(asab.Application):
	'''
	Run by:  
	`$ PYTHONPATH=.. ./webserver.py`
	
	The application is available at http://localhost:8080/hello
	'''

	def __init__(self):
		super().__init__()

		# Create the Web server
		web = asab.web.create_web_server(self, api = True)

		# Add a route to the handler method
		web.add_get('/hello', self.hello)

		print("Test with curl:\n\t$ curl http://localhost:8080/hello")


	# This is the web request handler
	async def hello(self, request):
		return asab.web.rest.json_response(request, data="Hello, world!\n")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
