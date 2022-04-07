import random
import asab
import aiohttp

import asab.web


class MyApplication(asab.Application):
	"""
	Listens on localhost:8080
	"""
	def __init__(self):
		super().__init__()

		# Initialize WebService
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		# Create remote connection endpoint
		web_app = self.WebContainer.WebApp
		web_app.router.add_get('/rc', self.rc)

		# To store future websocket connection
		self.WS = None

		# Periodically trigger "_on_tick" method:
		self.PubSub.subscribe("Application.tick/10!", self._on_tick)


	# Ensure that websocket gets closed in Application exit time
	async def finalize(self):
		if self.WS is not None:
			print("\N{PRINCESS} closing websocket connection...")
			await self.WS.send_str("Goodbye!")
			await self.WS.close()


	# Create websocket connection and waits for incoming messages
	async def rc(self, request):
		self.WS = aiohttp.web.WebSocketResponse()
		await self.WS.prepare(request)

		async for msg in self.WS:
			print("\N{UNICORN FACE} incoming message: {}".format(msg.data))
			await self.WS.send_str("I got your message :)")


	# Chat with client
	async def _on_tick(self, message_type):
		messages = ["Hi again!", "Server here!", "Next message in 10 seconds!", "I am a talkative server!", "I love to talk!", "Hi!", ":)"]
		if self.WS is not None:
			await self.WS.send_str(random.choice(messages))


if __name__ == "__main__":
	app = MyApplication()
	app.run()
