import asyncio
import aiohttp
import asab


class Subscriber(object):


	def __init__(self, app, pubsub, *message_types):
		self.PubSub = pubsub
		self.Loop = app.Loop

		for message_type in message_types:
			self.PubSub.subscribe(message_type, self._on_message)

		#TODO: Applicatio exit:
		# for ws in self.Websockets:
        #	await ws.close(code=WSCloseCode.GOING_AWAY, message='Server shutdown')
		self.Websockets = set([])


	async def _on_message(self, message_type, *args, **kwargs):
		message = {'message_type': message_type}
		if len(args) > 0:
			message['args'] = args
		if len(kwargs) > 0:
			message['kwargs'] = kwargs

		for ws in self.Websockets:
			await ws.send_json(message)


	async def __call__(self, request):
		ws = aiohttp.web.WebSocketResponse()
		await ws.prepare(request)

		try:
			self.Websockets.add(ws)

			async for msg in ws:
				# We receive a WSMessage from a peer
				#TODO: Handle this ...
				print(">>>", msg)

		except asyncio.CancelledError:
			pass

		finally:
			self.Websockets.remove(ws)

		return ws
