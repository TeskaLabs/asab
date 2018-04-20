#!/usr/bin/env python3
import os
import asab
import aiohttp

import asab.web
import asab.web.session

class MyApplication(asab.Application):

	'''
	Run by:
	$ PYTHONPATH=.. ./webserver.py
	'''

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Add a web session service
		asab.web.session.ServiceWebSession(self, "asab.ServiceWebSession", websvc)

		# Add a route
		websvc.WebApp.router.add_get('/api/login', self.login)
		print("Test with curl:\n\t$ curl http://localhost:8080/api/login")

		# Add a web app
		websvc.addFrontendWebApp('/', "webapp")


	async def login(self, request):
		session = request.get('Session')
		return aiohttp.web.Response(text='Hello {}!\n'.format(session))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
