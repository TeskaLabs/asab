import logging
import asyncio
import aiohttp
import asab

#

L = logging.getLogger(__name__)

#

class WebSocketFactory(object):

	'''
	websvc.WebApp.router.add_get('/api/ws', asab.web.WebSocketFactory(self))

	<script type="text/javascript">
		var connection = new WebSocket(((window.location.protocol === "https:") ? "wss://" : "ws://") + window.location.host + "/api/ws");
		connection.onmessage = function (e) {
			...
		};
	</script>

	'''


	def __init__(self, app):
		self.Loop = app.Loop
		self.WebSockets = set([])

		app.PubSub.subscribe("Application.stop!", self._on_app_stop)


	def _on_app_stop(self, message_type, counter):
		# Clean up during application exit
		wslist = [ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown') for ws in self.WebSockets]
		asyncio.gather(*wslist, loop=self.Loop)


	def send_parallely(self, send_futures):
		#THIS METHOD IS OBSOLETED, DON'T USE IT IN A NEW CODE.
	 	# Send messages parallely
	 	asyncio.gather(*send_futures, loop=self.Loop)


	async def __call__(self, request):
		ws = await self.on_request(request)

		try:
			self.WebSockets.add(ws)

			async for msg in ws:
				await self.on_message(request, ws, msg)

		except asyncio.CancelledError:
			await ws.close()

		finally:
			self.WebSockets.remove(ws)

		return ws


	async def on_request(self, request):
		'''
		Override this to initialize websocket:

		async def on_request(self, request):
			...
			ws = super().on_request(request)
			...
			return ws

		'''
		ws = aiohttp.web.WebSocketResponse()
		session = request.get('Session')
		if session is not None:
			await session.Storage.set(session, ws)
		await ws.prepare(request)
		return ws


	async def on_message(self, request, websocket, message):
		'''
		Override this method to receive messages from client over the websocket
		'''
		pass
