import os

import aiohttp

import asab
import asab.web


class MyApplication(asab.Application):
	"""
	Run a simple multi-user chat on http://localhost:8080/
	"""

	def __init__(self):
		super().__init__()

		# Initialize WebService
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		self.WebContainer.WebApp.router.add_get('/', self.index)

		self.WebSocketFactory = asab.web.WebSocketFactory(self)
		self.WebContainer.WebApp.router.add_get('/ws', self.WebSocketFactory)
		self.WebSocketFactory.on_message = self.on_message

	async def index(self, request):
		data = open(os.path.join(os.path.dirname(__file__), "websocket-chat.html"), 'r').read()
		return aiohttp.web.Response(text=data, content_type="text/html")

	async def on_message(self, websocket, message, wsid):
		if message.type == aiohttp.WSMsgType.TEXT:
			await self.WebSocketFactory.send_str_all(message.data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
