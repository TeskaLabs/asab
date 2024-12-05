import logging
import asyncio
import weakref
import functools
import typing


L = logging.getLogger(__name__)


class PubSub(object):
	"""
	Object for delivering messages across the ASAB application.

	A message is a function or coroutine with specific `message_type` that can be published and subscribed at various places in the code.
	"""


	def __init__(self, app):
		self.Subscribers = {}
		self.Loop = app.Loop


	def subscribe(self, message_type: str, callback: typing.Callable):
		"""
		Set `callback` that will be called when `message_type` is received.

		Args:
			message_type: Message to be subscribed to. It should end with an exclamation mark `"!"`.
			callback: Function or coroutine that is called when the message is received. `message_type` is passed as the first argument to the callback.

		Examples:

		```python
		class MyClass:
			def __init__(self, app):
				app.PubSub.subscribe("Application.tick!", self.on_tick)

			def on_tick(self, message_type):
				print(message_type)
		```
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
		Find all methods decorated by `@asab.subscribe` on the object and subscribe for them.

		Examples:

		```python
		class MyClass:
			def __init__(self, app):
				app.PubSub.subscribe_all(self)

			@asab.subscribe("Application.tick!")
			async def on_tick(self, message_type):
				print(message_type)

			@asab.subscribe("Application.exit!")
			def on_exit(self, message_type):
				print(message_type)
		```
		"""
		for member_name in dir(obj):
			member = getattr(obj, member_name)
			message_types = getattr(member, 'asab_pubsub_subscribe_to_message_types', None)
			if message_types is not None:
				for message_type in message_types:
					self.subscribe(message_type, member)


	def unsubscribe(self, message_type, callback):
		"""
		Remove `callback` from the subscribed `message_type`.

		When the subscription does not exist, warning is displayed.

		Examples:

		```python
		class MyClass:
			def __init__(self, app):
				app.PubSub.subscribe("Application.tick!", self.only_once)

			def only_once(self, message_type):
				print("This message is displayed only once!")
				app.PubSub.unsubscribe("Application.tick!", self.only_once)
		```
		"""
		callback_list = self.Subscribers.get(message_type)
		if callback_list is None:
			L.warning("Message type subscription '{}' not found.".format(message_type))
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
			L.warning("Subscriber '{}' not found for the message type '{}'.".format(message_type, callback))

		if remove_list is not None:
			for callback_ref in remove_list:
				callback_list.remove(callback_ref)

		if len(callback_list) == 0:
			del self.Subscribers[message_type]


	def _callback_iter(self, message_type):

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


	def publish(self, message_type: str, *args, **kwargs):
		"""
		Publish the message and notify the subscribers of an `message type`.

		`message_type` is passed as the first argument to the subscribed callback.

		Args:
			message_type: The emitted message.
			asynchronously (bool, optional): If `True`, `call_soon()` method will be used for the asynchronous delivery of the message. Defaults to `False`.

		Examples:

		```python
		class MyApplication(asab.Application):
			async def initialize(self):
				self.Count = 0
				self.PubSub.subscribe("Fireworks.started!", self.on_fireworks)

			async def main(self):
				for i in range(3):
					self.Count += 1
					self.PubSub.publish("Fireworks.started!", self.Count)
					await asyncio.sleep(1)

			def on_fireworks(self, message_type, count):
				print("boom " * count)
		```
		"""

		asynchronously = kwargs.pop('asynchronously', False)

		if asynchronously:
			for callback in self._callback_iter(message_type):
				self.Loop.call_soon(functools.partial(callback, message_type, *args, **kwargs))

		else:
			for callback in self._callback_iter(message_type):
				try:
					callback(message_type, *args, **kwargs)
				except Exception:
					L.exception("Error in a PubSub callback", struct_data={'message_type': message_type})


	def publish_threadsafe(self, message_type: str, *args, **kwargs):
		"""
		Publish the message and notify the subscribers of an `message type` safely form a different that main thread.

		`message_type` is passed as the first argument to the subscribed callback.

		Args:
			message_type: The emitted message.
			asynchronously (bool, optional): If `True`, `call_soon()` method will be used for the asynchronous delivery of the message. Defaults to `False`.
		"""
		def in_main_thread():
			try:
				self.publish(message_type, *args, **kwargs)
			except Exception:
				L.exception("Error in a PubSub threadsafe", struct_data={'message_type': message_type})
		self.Loop.call_soon_threadsafe(in_main_thread)


	async def message(self, message_type: str) -> tuple:
		"""
		Await specific message from a coroutine. It is a convenience method for the `Subscriber` object.

		Args:
			message_type: Message to be awaited.

		Returns:
			Triple (message_type, args, kwargs).

		Examples:

		```python
		message_type, args, kwargs = await self.PubSub.message("Library.ready!")
		```
		"""
		subscriber = Subscriber(self, message_type)
		message_type, args, kwargs = await subscriber.message()
		return message_type, args, kwargs


class subscribe(object):
	"""
	Decorator function that simplifies the process of subscription together with `PubSub.subscribe_all()` method.

	Examples:
	```python
	class MyClass(object):
		def __init__(self, app):
			app.PubSub.subscribe_all(self)

		@asab.subscribe("Application.tick!")
		async def on_tick(self, message_type):
			print(message_type)

		@asab.subscribe("Application.exit!")
		def on_exit(self, message_type):
			print(message_type)
	```
	"""


	def __init__(self, message_type):
		self.message_type = message_type


	def __call__(self, f):
		if getattr(f, 'asab_pubsub_subscribe_to_message_types', None) is None:
			f.asab_pubsub_subscribe_to_message_types = [self.message_type]
		else:
			f.asab_pubsub_subscribe_to_message_types.append(self.message_type)
		return f


def _deliver_async_exited(task):
	try:
		task.result()
	except asyncio.CancelledError:
		pass
	except Exception:
		L.exception("Error during pubsub delivery", struct_data={'task': task.get_name()})


def _deliver_async(loop, callback, message_type, *args, **kwargs):
	task = asyncio.create_task(callback(message_type, *args, **kwargs))
	task.set_name("asab.PubSub.{}".format(message_type))
	task.add_done_callback(_deliver_async_exited)


class Subscriber(object):
	"""
	Object for consuming PubSub messages in coroutines.

	It subscribes for various message types and consumes them.
	It is built on (first-in, first-out) basis.
	If `pubsub` argument is `None`, the initial subscription is skipped.

	Examples:

	The example of the subscriber object usage in async for statement:

	```python
	async def my_coroutine(self):
		# Subscribe for two application events
		subscriber = asab.Subscriber(
			self.PubSub,
			"Application.tick!",
			"Application.exit!"
		)
		async for message_type, args, kwargs in subscriber:
			if message_type == "Application.exit!":
				break;
			print("Tick.")
	```
	"""

	def __init__(self, pubsub=None, *message_types):

		self._q = asyncio.Queue()
		self._subscriptions = []

		if pubsub is not None:
			for message_type in message_types:
				self.subscribe(pubsub, message_type)


	def subscribe(self, pubsub, message_type):
		"""
		Subscribe for more message types. This method can be called many times with various `pubsub` objects.
		"""
		pubsub.subscribe(message_type, self)
		self._subscriptions.append((pubsub, message_type))


	def __call__(self, message_type, *args, **kwargs):
		self._q.put_nowait((message_type, args, kwargs))


	def message(self):
		"""
		Wait for a message asynchronously and return triple `(message_type, args, kwargs)`.

		Examples:

		```python
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
		```
		"""
		return self._q.get()


	def __aiter__(self):
		return self


	async def __anext__(self):
		return await self._q.get()
