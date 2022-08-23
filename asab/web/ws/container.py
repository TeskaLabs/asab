import logging
import dataclasses

import aiohttp


L = logging.getLogger(__name__)


@dataclasses.dataclass
class Message:
	id: str
	msg: bytes


class WebSocketContainer():
	def __init__(self, ws, id, svc):
		self.ID = id
		self.WS = ws
		self.Messages = list()
		self.WebSocketService = svc

	async def await_messages(self):
		async for msg in self.WS:
			if msg.type == aiohttp.WSMsgType.TEXT:
				self.save_incoming_msg(msg)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				L.warning("Error message from WS: {}".format(msg))
				L.warning("WS exception: {}".format(await self.WS.exception()))
				# TODO: What should I do with this error?
				continue

	def save_incoming_msg(self, msg):
		m = Message(self.ID, msg.data)
		self.Messages.append(m)
		self.WebSocketService.MessageArrived.set()  # Signals that response came and can be correlated to request
