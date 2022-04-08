import random
import asab
import aiohttp

import asab.web


class MyApplication(asab.Application):
	"""
	Listens on localhost:8080
	Talks to "websocket_client" example
	"""

	def __init__(self):
		super().__init__()

		# Initialize WebService
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		# Create remote connection endpoint
		web_app = self.WebContainer.WebApp
		web_app.router.add_get("/rc", self.rc)

		# To store future websocket connection
		self.WS = None

		# Periodically trigger "_on_tick" method:
		self.PubSub.subscribe("Application.tick/10!", self._on_tick)


	async def finalize(self):
		"""
		Ensures that websocket gets closed in Application exit time
		"""
		if self.WS is not None:
			print("\N{PRINCESS} closing websocket connection...")
			await self.WS.send_str("Goodbye!")
			await self.WS.close()


	async def rc(self, request):
		"""
		Creates websocket connection and waits for incoming messages
		"""
		self.WS = aiohttp.web.WebSocketResponse()
		await self.WS.prepare(request)

		async for msg in self.WS:
			print("\N{UNICORN FACE} incoming message: {}".format(msg.data))
			await self.WS.send_str("I got your message :)")


	async def _on_tick(self, message_type):
		"""
		Chats with client.
		If there is connection, checks whther is it alive. If yes, it sends message to the websocket. Otherwise discards the connection (self.WS = None).
		"""
		messages = [
			"Hi, who's there?",
			"How much is 5 + 2 ?",
			"Next message in 10 seconds!",
			"I am a talkative server!",
			"I love to talk!",
			"Hi!",
			"I'm tired. Get off!",
		]

		if self.WS is not None:
			try:
				await self.WS.ping()
			except (ConnectionResetError, RuntimeError):
				print("Connection is dead :(")
				self.WS = None
				return
			await self.WS.send_str(random.choice(messages))



if __name__ == "__main__":
	app = MyApplication()
	app.run()
