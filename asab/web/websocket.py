import logging
import asyncio
import aiohttp

from ..log import LOG_NOTICE

#

L = logging.getLogger(__name__)

#


class WebSocketFactory(object):

	'''
	wsfactory = asab.web.WebSocketFactory(self)
	websvc.WebApp.router.add_get('/api/ws', wsfactory)
	wsfactory.on_message = ...


	Javascript example:

	<script type="text/javascript">
		var connection = new WebSocket(((window.location.protocol === "https:") ? "wss://" : "ws://") + window.location.host + "/api/ws");
		connection.onmessage = function (e) {
			...
		};
	</script>

	'''


	def __init__(self, app, *, timeout=10.0, protocols=(), compress=True, max_msg_size=4194304):
		self.Counter = 0
		self.WebSockets = {}

		self.Timeout = timeout
		self.Protocols = protocols
		self.Compress = compress
		self.MaxMsgSize = max_msg_size
		self.__doc__ = "Provides WebSocket connection. Requires WebSocket upgrade."

		app.PubSub.subscribe("Application.stop!", self._on_app_stop)


	async def _on_app_stop(self, message_type, counter):
		# Clean up during application exit
		await self.close_all(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')


	async def close_all(self, *, code=aiohttp.WSCloseCode.OK, message=b''):
		'''
		Close all websockets
		'''
		await asyncio.gather(
			*[ws.close(code=code, message=message) for ws in self.WebSockets.values()],
			return_exceptions=True
		)


	async def ping_all(self):
		'''
		Ping all connected websockets
		'''
		await asyncio.gather(
			*[ws.ping() for ws in self.WebSockets.values()],
			return_exceptions=True
		)


	async def send_str_all(self, data, compress=None):
		'''
		Send string to all connected websockets
		'''
		await asyncio.gather(
			*[ws.send_str(data, compress=compress) for ws in self.WebSockets.values()],
			return_exceptions=True
		)

	async def send_json_all(self, data, compress=None):
		'''
		Send json to all connected websockets
		'''
		await asyncio.gather(
			*[ws.send_json(data, compress=compress) for ws in self.WebSockets.values()],
			return_exceptions=True
		)


	def get(self, wsid):
		'''
		Get a websocket using its wsid.

		IMPORTANT: This method can return None if the websocket has been already closed.
		'''
		return self.WebSockets.get(wsid)


	async def __call__(self, request):
		ws = aiohttp.web.WebSocketResponse(
			timeout=self.Timeout,
			protocols=self.Protocols,
			compress=self.Compress,
			max_msg_size=self.MaxMsgSize,
		)

		await ws.prepare(request)

		L.log(LOG_NOTICE, "Websocket connection accepted")

		wsid = await self.register(ws, request)

		try:
			self.WebSockets[wsid] = ws
			await self.on_connect(ws, wsid)

			async for msg in ws:
				if msg.type == aiohttp.WSMsgType.ERROR:
					break
				else:
					await self.on_message(ws, msg, wsid)

		except asyncio.CancelledError:
			await ws.close()

		finally:
			del self.WebSockets[wsid]
			L.log(LOG_NOTICE, "Websocket connection closed")
			await self.on_close(ws, wsid)

		return ws


	async def register(self, ws, request):
		'''
		Must return the unique identifier of the websocket `wsid`.
		The default implementation is the unique counter.
		You may overload this to provide custom unique identifier
		'''
		self.Counter += 1
		return self.Counter


	async def on_connect(self, websocket, wsid):
		'''
		Override this method to implement action on websocket connection
		'''
		pass


	async def on_message(self, websocket, message, wsid):
		'''
		Override this method to receive messages from client over the websocket
		'''
		pass


	async def on_close(self, websocket, wsid):
		'''
		Override this method to receive a notification that client closed the websocket connection
		'''
		pass
