import logging
import asyncio
import inspect
import functools

#

L = logging.getLogger(__name__)

#


class PubSub(object):

	def __init__(self, app):
		self.subscribers = {}
		self.Loop = app.Loop


	def subscribe(self, message_type, callback):
		"""
		Subscribe a subscriber to the an message type.
		It could be even plain function, method or its coroutine variant (then it will be delivered in a dedicated future)
		"""

		def _deliver_async(loop, callback, message_type, *args, **kwargs):
			asyncio.ensure_future(callback(message_type, *args, **kwargs), loop=loop)

		# If subscribe is a coroutine (async def), then wrap delivery in 
		if inspect.iscoroutinefunction(callback):
			callback = functools.partial(_deliver_async, self.Loop, callback)

		if message_type not in self.subscribers:
			self.subscribers[message_type] = set([callback])
		else:
			self.subscribers[message_type].add(callback)


	def subscribe_all(self, obj):
		"""
		Find all @asab.subscribe decorated methods on the obj and do subscription
		"""
		for member_name in dir(obj):
			member = getattr(obj, member_name)
			message_types = getattr(member, 'asab_pubsub_subscribe_to_message_types', None)
			if message_types is not None:
				for message_type in message_types:
					self.subscribe(message_type, member)


	def unsubscribe(self, message_type, callback):
		""" Remove a subscriber of an message type from the set. """

		callback_set = self.subscribers.get(message_type)
		if callback_set is None:
			L.warning("Message type subscription '{}'' not found.".format(message_type))
			return
		else:
			try:
				callback_set.remove(callback)
			except KeyError:
				L.warning("Subscriber '{}'' not found for the message type '{}'.".format(message_type, callback))


	def publish(self, message_type, *args, **kwargs):
		""" Notify subscribers of an message type. Including arguments. """

		callback_set = self.subscribers.get(message_type)
		if callback_set is None:
			return

		asynchronously = kwargs.pop('asynchronously', False)

		if asynchronously:
			for callback in callback_set:
				self.Loop.call_soon(functools.partial(callback, message_type, *args, **kwargs))

		else:
			for callback in callback_set:
				callback(message_type, *args, **kwargs)

###

class subscribe(object):

	'''
	Decorator

	Usage:
	
	@asab.subscribe("tick")
	def on_tick(self, message_type):
	print("Service tick")
	'''

	def __init__(self, message_type):
		self.message_type = message_type

	def __call__(self, f):
		if getattr(f, 'asab_pubsub_subscribe_to_message_types', None) is None:
			f.asab_pubsub_subscribe_to_message_types = [self.message_type]
		else:
			f.asab_pubsub_subscribe_to_message_types.append(self.message_type)
		return f

