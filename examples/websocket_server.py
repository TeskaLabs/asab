import random
import asab

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
		web_app.router.add_get("/ws", self.ws)

		from asab.web.ws import WebSocketService
		self.WebSocketService = WebSocketService(self)

		self.TaskService = self.get_service("asab.TaskService")
		self.TaskService.schedule(self.read_messages())

		self.WantToRead = True

		# Periodically trigger "_on_tick" method:
		self.PubSub.subscribe("Application.tick/10!", self._on_tick)

	async def finalize(self):
		self.WantToRead = False

	async def ws(self, request):
		return await self.WebSocketService.add_ws(request)

	async def read_messages(self):
		while True:
			m_list = await self.WebSocketService.read()
			print("\N{UNICORN FACE}", m_list)
			if not m_list:
				return


	async def _on_tick(self, message_type):
		"""
		Chats with client.
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
		await self.WebSocketService.send(random.choice(messages))


if __name__ == "__main__":
	app = MyApplication()
	app.run()
