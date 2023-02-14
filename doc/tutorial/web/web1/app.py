#!/usr/bin/env python3
import asab.web.rest


class MyWebApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Create the Web server
		web = asab.web.create_web_server(self)

		# Add a route to the handler method
		web.add_get('/hello', self.hello)

	# This is the web request handler
	async def hello(self, request):
		return asab.web.rest.json_response(request, data="Hello, world!\n")


if __name__ == '__main__':
	app = MyWebApplication()
	app.run()
