import logging
import asyncio

from typing import List, Union, Dict, AnyStr
import uuid

import aiohttp.web

from ...abc.service import Service
from .container import WebSocketContainer



L = logging.getLogger(__name__)


class WebSocketService(Service):

	def __init__(self, app, service_name="asab.WebSocketService"):
		super().__init__(app, service_name)
		self.WebSockets = dict()
		self.MessageArrived = asyncio.Event()
		self.InRuntime = True

		self.TaskService = self.App.get_service("asab.TaskService")
		self.App.PubSub.subscribe("Application/10!", self._on_tick_healthcheck)

	async def finalize(self, app):
		"""
		Ensures that websockets get closed in Application exit time
		"""
		self.InRuntime = False
		for wsc in self.WebSockets.values():
			await wsc.WS.close()

	async def add_ws(self, request, id: str = None):
		ws = aiohttp.web.WebSocketResponse()
		await ws.prepare(request)
		if not id:
			id = str(uuid.uuid4())
		wsc = WebSocketContainer(ws, id, self)
		self.WebSockets[id] = wsc
		await wsc.await_messages()
		return ws


	async def read(self) -> List:
		while True:
			if not self.InRuntime:
				return False
			messages = list()

			for wsc in self.WebSockets.values():
				while len(wsc.Messages) > 0:
					messages.append(wsc.Messages.pop())

			if messages:
				return messages

			await self.MessageArrived.wait()
			self.MessageArrived.clear()


	async def send(self, data: Union[Dict, AnyStr]):
		for wsc in self.WebSockets.values():
			await _do_send(wsc, data)


	def _on_tick_healthcheck(self, message_type):
		self.TaskService.schedule(self._discard_dead_connections())


	async def _discard_dead_connections(self):

		dead_connections = []

		for id, wsc in self.WebSockets.items():
			try:
				await wsc.WS.ping()
			except (ConnectionResetError, RuntimeError):
				L.info("WebSocket with id '{}' disconnected.".format(id))
				dead_connections.append(id)

		for id in dead_connections:
			del self.WebSockets[id]


async def _do_send(wsc, data):
	try:
		await wsc.WS.ping()
	except (ConnectionResetError, RuntimeError):
		return

	if isinstance(data, bytes):
		await wsc.WS.send_bytes(data)
	elif isinstance(data, str):
		await wsc.WS.send_str(data)
	elif isinstance(data, dict):
		await wsc.WS.send_json(data)
	else:
		L.warning("Unknown data type to send through WebSocket: '{}'".format(type(data)))
