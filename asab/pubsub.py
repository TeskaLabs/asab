import logging
import asyncio
import weakref
import functools


L = logging.getLogger(__name__)


class PubSub(object):


	def __init__(self, app):
		self.Subscribers = {}
		self.Loop = app.Loop


	def subscribe(self, message_type, callback):
		"""
		Subscribe a subscriber to the an message type.
		It could be even plain function, method or its coroutine variant (then it will be delivered in a dedicated future)
		"""

		# If subscribe is a bound method, do special treatment
		# https://stackoverflow.com/questions/53225/how-do-you-check-whether-a-python-method-is-bound-or-not
		if hasattr(callback, '__self__'):
			callback = weakref.WeakMethod(callback)

		else:
			callback = weakref.ref(callback)

		if message_type not in self.Subscribers:
			self.Subscribers[message_type] = [callback]
		else:
			self.Subscribers[message_type].append(callback)


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

		callback_list = self.Subscribers.get(message_type)
		if callback_list is None:
			L.warning("Message type subscription '{}'' not found.".format(message_type))
			return

		remove_list = None

		for i in range(len(callback_list)):
			# Take an weakref entry in the callback list and references it
			c = callback_list[i]()

			# Check if a weak reference is working
			if c is None:  # a reference is lost, remove this entry
				if remove_list is None:
					remove_list = list()
				remove_list.append(callback_list[i])
				continue

			if c == callback:
				callback_list.pop(i)
				break

		else:
			L.warning("Subscriber '{}'' not found for the message type '{}'.".format(message_type, callback))

		if remove_list is not None:
			for callback_ref in remove_list:
				callback_list.remove(callback_ref)

		if len(callback_list) == 0:
			del self.Subscribers['message_type']


	def _callback_iter(self, message_type):

		def _deliver_async(loop, callback, message_type, *args, **kwargs):
			asyncio.ensure_future(callback(message_type, *args, **kwargs), loop=loop)

		callback_list = self.Subscribers.get(message_type)
		if callback_list is None:
			return

		remove_list = None

		for callback_ref in callback_list:
			callback = callback_ref()

			# Check if a weak reference is working
			if callback is None:  # a reference is lost
				if remove_list is None:
					remove_list = list()
				remove_list.append(callback_ref)
				continue

			if asyncio.iscoroutinefunction(callback):
				callback = functools.partial(_deliver_async, self.Loop, callback)

			yield callback

		if remove_list is not None:
			for callback_ref in remove_list:
				callback_list.remove(callback_ref)


	def publish(self, message_type, *args, **kwargs):
		""" Notify subscribers of an message type. Including arguments. """

		asynchronously = kwargs.pop('asynchronously', False)

		if asynchronously:
			for callback in self._callback_iter(message_type):
				self.Loop.call_soon(functools.partial(callback, message_type, *args, **kwargs))

		else:
			for callback in self._callback_iter(message_type):
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


###

class Subscriber(object):

	'''
:any:`Subscriber` object allows to consume PubSub messages in coroutines.
It subscribes for various message types and consumes them.
It works on FIFO basis (First message In, first message Out).
If ``pubsub`` argument is None, the initial subscription is skipped.

.. code:: python

	subscriber = asab.Subscriber(
		app.PubSub,
		"Application.tick!",
		"Application.stop!"
	)
	'''

	def __init__(self, pubsub=None, *message_types):

		self._q = asyncio.Queue()
		self._subscriptions = []

		if pubsub is not None:
			for message_type in message_types:
				self.subscribe(pubsub, message_type)


	def subscribe(self, pubsub, message_type):
		'''
Subscribe for more message types. This method can be called many times with various ``pubsub`` objects.
		'''
		pubsub.subscribe(message_type, self)
		self._subscriptions.append((pubsub, message_type))


	def __call__(self, message_type, *args, **kwargs):
		self._q.put_nowait((message_type, args, kwargs))


	def message(self):
		'''
Wait for a message asynchronously.
Returns a three-members tuple ``(message_type, args, kwargs)``.

Example of the `await message()` use:

.. code:: python

	async def my_coroutine(app):
		# Subscribe for a two application events
		subscriber = asab.Subscriber(
			app.PubSub,
			"Application.tick!",
			"Application.exit!"
		)
		while True:
			message_type, args, kwargs = await subscriber.message()
			if message_type == "Application.exit!":
				break
			print("Tick.")

		'''
		return self._q.get()


	def __aiter__(self):
		return self


	async def __anext__(self):
		return await self._q.get()
