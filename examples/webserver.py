#!/usr/bin/env python3
import os
import weakref
import asyncio
import asab
import aiohttp

import asab.web
import asab.web.rest
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
		asab.web.session.ServiceWebSession(self, "asab.ServiceWebSession", websvc, session_class=MySession)

		# Enable exception to JSON exception middleware
		websvc.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		websvc.WebApp.router.add_get('/api/login', self.login)
		print("Test with curl:\n\t$ curl http://localhost:8080/api/login")

		websvc.WebApp.router.add_get('/error', self.error)

		# Add a web app
		websvc.add_frontend_web_app('/', "webapp")

		# Add a websocket handler
		websvc.WebApp.router.add_get('/subscribe', MyWebSocketFactory(self))


	async def login(self, request):
		session = request.get('Session')
		return aiohttp.web.Response(text='Hello {}!\n'.format(session))


	async def error(self, request):
		raise RuntimeError("Errror!!")


class MyWebSocketFactory(asab.web.WebSocketFactory):

	def __init__(self, app):
		super().__init__(app)

		app.PubSub.subscribe("Application.tick/10!", self.on_tick)


	async def on_request(self, request):
		session = request.get('Session')
		ws = await super().on_request(request)
		session.WebSockets.add(ws)
		return ws


	async def on_message(self, request, websocket, message):
		print("WebSocket message", message)


	def on_tick(self, event_name):
		message = {'event_name': event_name, 'type': 'factory'}

		wsc = list()
		for ws in self.WebSockets:
			wsc.append(ws.send_json(message))

		self.send_parallely(wsc)


class MySession(asab.web.session.Session):

	def __init__(self, storage, id, new, max_age=None):
		super().__init__(storage, id, new, max_age)
		storage.App.PubSub.subscribe("Application.tick!", self.on_tick)

		self.Loop = storage.App.Loop
		self.WebSockets = weakref.WeakSet()



	def on_tick(self, event_name):
		message = {'event_name': event_name, 'type': 'session'}

		wsc = list()
		for ws in self.WebSockets:
			wsc.append(ws.send_json(message))

		asyncio.gather(*wsc, loop=self.Loop)




if __name__ == '__main__':
	app = MyApplication()
	app.run()
