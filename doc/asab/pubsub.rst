Publish-Subscribe
=================

.. py:currentmodule:: asab

Publish–subscribe is a messaging pattern where senders of messages, called publishers, send the messages to receivers, called subscribers, via PubSub message bus. Publishers don't directly interact with subscribers in any way. Similarly, subscribers express interest in one or more message types and only receive messages that are of interest, without knowledge of which publishers, if any, there are.

.. py:class:: PubSub(app)

ASAB ``PubSub`` operates with a simple messages, defined by their *message type*, which is a string.
We recommend to add ``!`` (explamation mark) at the end of the message type in order to distinguish this object from other types such as Python class names or functions.
Example of the message type is e.g. :any:`Application.run!` or :any:`Application.tick/600!`.

The message can carry an optional positional and keyword arguments.
The delivery of a message is implemented as a the standard Python function.


*Note:* There is an default, application-wide Publish-Subscribe message bus at :any:`Application.PubSub` that can be used to send messages.
Alternatively, you can create your own instance of :py:class:`PubSub` and enjoy isolated PubSub delivery space.


Subscription
------------

.. py:method:: PubSub.subscribe(message_type, callback)

Subscribe to a message type. Messages will be delivered to a ``callback`` callable (function or method).
The ``callback`` can be a standard callable or an ``async`` coroutine.
Asynchronous ``callback`` means that the delivery of the message will happen in a coroutine, asynchronously.

``Callback`` callable will be called with the first argument

Example of a subscription to an :any:`Application.tick!` messages.

.. code:: python

	class MyClass(object):
	    def __init__(self, app):
	        app.PubSub.subscribe("Application.tick!", self.on_tick)

	    def on_tick(self, message_type):
	        print(message_type)


Asynchronous version of the above:

.. code:: python

	class MyClass(object):
	    def __init__(self, app):
	        app.PubSub.subscribe("Application.tick!", self.on_tick)

	    async def on_tick(self, message_type):
	    	await asyncio.sleep(5)
	        print(message_type)


.. py:method:: PubSub.subscribe_all(obj)

To simplify the process of subscription to :any:`PubSub`, ASAB offers the decorator-based *"subscribe all"* functionality.


In the followin example, both ``on_tick()`` and ``on_exit()`` methods are subscribed to :any:`Application.PubSub` message bus.

.. code:: python

	class MyClass(object):
	    def __init__(self, app):
	        app.PubSub.subscribe_all(self)

	    @asab.subscribe("Application.tick!")
	    async def on_tick(self, message_type):
	        print(message_type)

	    @asab.subscribe("Application.exit!")
	    def on_exit(self, message_type):
	        print(message_type)


.. py:method:: PubSub.unsubscribe(message_type, callback)

Unsubscribe from a message delivery.


.. autoclass:: asab.Subscriber
    :members:
    :undoc-members:


Publishing
----------

.. py:method:: PubSub.publish(message_type, \*args, \**kwargs)

Publish a message to the PubSub message bus.
It will be delivered to each subscriber synchronously.
It means that the method returns after each subscribed ``callback`` is called.

The example of a message publish to the :any:`Application.PubSub` message bus:

.. code:: python

	def my_function(app):
	    app.PubSub.publish("mymessage!")


Asynchronous message delivery can be trigged by providing ``asynchronously=True`` keyword argument.
Each subscriber is then handled in a dedicated ``Future`` object.
The method returns immediatelly and the delivery of the message to subscribers happens, when control returns to the event loop.

The example of a **asynchronous version** of a message publish to the :any:`Application.PubSub` message bus:

.. code:: python

	def my_function(app):
	    app.PubSub.publish("mymessage!", asynchronously=True)
