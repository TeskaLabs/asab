#!/usr/bin/env python3
import asab
import asab.web
import aiohttp.web

class MyWebApplication(asab.Application):

	async def initialize(self):
		self.add_module(asab.web.Module)
		websvc = self.get_service("asab.WebService")
		websvc.WebApp.router.add_get('/', self.index)

	async def index(self, request):
		return aiohttp.web.Response(text='Hello, world.\n')

if __name__ == '__main__':
	app = MyWebApplication()
	app.run()
