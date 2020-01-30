import logging
import json
import asyncio

import aiohttp


L = logging.getLogger(__name__)


class LogManIOWebSocketUplink(object):


	def __init__(self, app, url, queue):
		self.App = app
		self.URL = url
		self.OutboundQueue = queue

		self.SenderFuture = None
		self.ReceiverFuture = None

		self.Running = True


	async def initialize(self, app):
		self._reconnect()


	async def finalize(self, app):
		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None

		if self.ReceiverFuture is not None:
			self.ReceiverFuture.cancel()
			self.ReceiverFuture = None


	def _reconnect(self):
		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None

		if self.ReceiverFuture is not None:
			self.ReceiverFuture.cancel()
			self.ReceiverFuture = None

		self.ReceiverFuture = asyncio.ensure_future(self._receiver(), loop=self.App.Loop)
		self.ReceiverFuture.add_done_callback(self._on_done)


	async def _receiver(self):
		try:
			async with aiohttp.ClientSession() as session:
				async with session.ws_connect(self.URL) as ws:
					await ws.ping()
					# We are connected :-)

					assert(self.SenderFuture is None)
					self.SenderFuture = asyncio.ensure_future(self._sender(ws), loop=self.App.Loop)
					self.SenderFuture.add_done_callback(self._on_done)

					async for msg in ws:
						pass

		except aiohttp.client_exceptions.ClientConnectorError as e:
			L.error("LogMan.io {}".format(e))


	async def _sender(self, ws):
		while self.Running:
			msg_type, body = await self.OutboundQueue.get()
			if isinstance(body, dict):
				body = json.dumps(body)
			await ws.send_str(msg_type + ' ' + body)


	def _on_done(self, future):
		try:
			future.result()
		except asyncio.CancelledError:
			pass
		except BaseException:
			L.exception("Error in LogMan.io websocket:")

		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None

		if self.ReceiverFuture is not None:
			self.ReceiverFuture.cancel()
			self.ReceiverFuture = None

			if self.Running:
				L.warning("LogMan.io reconnect in 5 secs.")
				self.App.Loop.call_later(5, self._reconnect)
