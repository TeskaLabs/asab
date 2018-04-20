import asyncio
import aiohttp
import asab


class Subscriber(object):


	def __init__(self, app, pubsub, *message_types):
		self.PubSub = pubsub
		self.Loop = app.Loop
		self.MessageTypes = message_types

		#TODO: Applicatio exit:
		# for ws in self.Websockets:
        #	await ws.close(code=WSCloseCode.GOING_AWAY, message='Server shutdown')
		self.Websockets = set([])


	async def __call__(self, request):
		ws = aiohttp.web.WebSocketResponse()
		await ws.prepare(request)

		try:
			self.Websockets.add(ws)

			subscriber = asab.Subscriber(self.PubSub, *self.MessageTypes)
			pending = set([subscriber.message(), ws.receive()])
			while True:
				done, pending = await asyncio.wait(pending, loop=self.Loop, return_when=asyncio.FIRST_COMPLETED)

				for x in done:
					x = x.result()
					if isinstance(x, aiohttp.WSMessage):
						# We receive a WSMessage from a peer
						#TODO: Handle this ...
						pending.add(ws.receive())

					else:
						# We receive a PubSub message
						message_type, args, kwargs = x
						message = {'message_type': message_type}
						if len(args) > 0:
							message['args'] = args
						if len(kwargs) > 0:
							message['kwargs'] = args

						await ws.send_json(message)
						pending.add(subscriber.message())

		except asyncio.CancelledError:
			pass

		finally:
			self.Websockets.remove(ws)

		return ws
