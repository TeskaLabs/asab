import logging
import asyncio
import aiohttp
import asab

#

L = logging.getLogger(__name__)

#

class Subscriber(object):

	'''

	websvc.WebApp.router.add_get('/subscribe', asab.web.Subscriber(self, self.PubSub, "Application.tick!"))


	<script type="text/javascript">
		var connection = new WebSocket(((window.location.protocol === "https:") ? "wss://" : "ws://") + window.location.host + "/subscribe");
		connection.onmessage = function (e) {
			...
		};
	</script>

	'''


	def __init__(self, app, pubsub, *message_types):
		self.PubSub = pubsub
		self.Loop = app.Loop
		self.Websockets = set([])

		for message_type in message_types:
			self.PubSub.subscribe(message_type, self._on_message)

		app.PubSub.subscribe("Application.stop!", self._on_app_stop)


	def _on_app_stop(self, message_type, counter):
		# Clean up during pplication exit
		wslist = [ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown') for ws in self.Websockets]
		asyncio.gather(*wslist, loop=self.Loop)


	def _on_message(self, message_type, *args, **kwargs):
		message = {'message_type': message_type}
		if len(args) > 0:
			message['args'] = args
		if len(kwargs) > 0:
			message['kwargs'] = kwargs

		wsc = list()
		for ws in self.Websockets:
			wsc.append(ws.send_json(message))

		# Send messages parallely
		asyncio.gather(*wsc, loop=self.Loop)


	async def __call__(self, request):
		ws = aiohttp.web.WebSocketResponse()
		await ws.prepare(request)

		try:
			self.Websockets.add(ws)

			async for msg in ws:
				L.warn("Received unexpected message from client: {}".msg)

		except asyncio.CancelledError:
			ws.close()

		finally:
			self.Websockets.remove(ws)

		return ws
