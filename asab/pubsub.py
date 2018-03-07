import logging
import asyncio

#

L = logging.getLogger(__name__)

#


class PubSub(object):
	"""
	Register subscribers and notify them when an event occurs.
	For architecture details refer to: https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern
	"""

	def __init__(self, app):
		self.subscribers = {}
		self.Loop = app.Loop


	def subscribe(self, event_name, callback):
		"""
		Add a subscriber of an event to the set.
		"""

		if event_name not in self.subscribers:
			self.subscribers[event_name] = set([callback])
		else:
			self.subscribers[event_name].add(callback)


	def subscribe_all(self, obj):
		"""
		Find all @asab.subscribe decorated methods on the obj and do subscription
		"""
		for member_name in dir(obj):
			member = getattr(obj, member_name)
			event_names = getattr(member, 'asab_pubsub_subscribe_to_event_names', None)
			if event_names is not None:
				for event_name in event_names:
					self.subscribe(event_name, member)


	def unsubscribe(self, event_name, callback):
		""" Remove a subscriber of an event from the set. """

		callback_set = self.subscribers.get(event_name)
		if callback_set is None:
			L.warning('Event name {} not found.'.format(event_name))
			return
		else:
			try:
				callback_set.remove(callback)
			except KeyError:
				L.warning('Callback {} not found in the event set {}.'.format(event_name, callback))


	def publish(self, event_name, *args, **kwargs):
		""" Notify subscribers of an event with arguments. """

		callback_set = self.subscribers.get(event_name)
		if callback_set is None:
			return

		for callback in callback_set:
			callback(event_name, *args, **kwargs)


	def publish_async(self, event_name, *args, **kwargs):
		""" Notify subscribers of an event with arguments asynchronously using coroutines. """

		async def publish_coro(callback, *args, **kwargs):
			callback(event_name, *args, **kwargs)

		callback_set = self.subscribers.get(event_name)
		if callback_set is None:
			return

		for callback in callback_set:
			asyncio.ensure_future(publish_coro(callback, *args, **kwargs), loop=self.Loop)

###

class subscribe(object):

	'''
	Decorator

	Usage:
	
	@asab.subscribe("tick")
	def on_tick(self, event_name):
	print("Service tick")
	'''

	def __init__(self, event_name):
		self.event_name = event_name

	def __call__(self, f):
		if getattr(f, 'asab_pubsub_subscribe_to_event_names', None) is None:
			f.asab_pubsub_subscribe_to_event_names = [self.event_name]
		else:
			f.asab_pubsub_subscribe_to_event_names.append(self.event_name)
		return f

