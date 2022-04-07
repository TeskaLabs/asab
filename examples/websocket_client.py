import random
import asyncio
import logging
import asab
import aiohttp

import asab.web

L = logging.getLogger(__name__)


# Fake config file
asab.Config.read_string("""
[rc]
ws=http://localhost:8080/rc
		""")


class MyApplication(asab.Application):
	"""
	Listens on localhost:8080
	Talks to websocket client
	"""
	def __init__(self):
		super().__init__()

		self.Task = None
		# Calls `_on_tick` method every second
		self.PubSub.subscribe("Application.tick!", self._on_tick)


	async def finalize(self):
		"""
		Ensures that before Application exits, all Tasks are done, Exceptions logged and websocket connection closed.
		"""
		self.PubSub.unsubscribe("Application.tick!", self._on_tick)

		self.Task.cancel()
		await self._collect_task()


	async def _on_tick(self, message_type):
		'''
		Checks for connection and connects if there's none.
		'''
		if self.Task is not None and self.Task.done():
			await self._collect_task()
			self.Task = None
		if self.Task is None:
			self.Task = asyncio.ensure_future(self._connect(), loop=self.Loop)


	async def _collect_task(self):
		"""
		Ensures that all tasks are awaited and Exceptions logged.
		"""
		try:
			await self.Task
		except asyncio.CancelledError:
			pass
		except Exception as e:
			L.warning(e)


	async def _connect(self):
		"""
		Creates new session and connects to server.
		Calls dispatcher whenever a message comes.
		"""
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(asab.Config.get("rc", "ws")) as ws:
				async for msg in ws:
					if msg.type == aiohttp.WSMsgType.TEXT:
						cont = await self.dispatch(msg)
						if cont is False:
							print("Connection interrupted.")
							break
						elif isinstance(cont, str):
							await ws.send_str(cont)
					elif msg.type == aiohttp.WSMsgType.ERROR:
						break
				await ws.close()


	async def dispatch(self, msg):
		"""
		Sorts incoming messages and prepares responses which are sent through the websocket back to the server.
		"""
		print("\N{TIGER} message from server: {}".format(msg.data))
		if msg.data == "Hi, who's there?":
			return "Hello, this is client!"
		elif msg.data == "I'm tired. Get off!":
			return False
		elif msg.data.startswith("How much is"):
			return self.count(msg.data)

	def count(self, msg):
		return str(random.randint(0, 10) + random.randint(0, 10))



if __name__ == "__main__":
	app = MyApplication()
	app.run()
