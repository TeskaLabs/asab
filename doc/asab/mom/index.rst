The message-oriented middleware
===============================

Message-oriented middleware (MOM) sends and receive messages between distributed systems.
MOM allows application components to be distributed over heterogeneous platforms and reduces the complexity of developing such applications.
The middleware creates a distributed communications layer that insulates the application developer from the details of the various  network interfaces.
It is a typical component of the microservice architecture, used for asynchronous tasks, complements synchronous HTTP REST API.

MOM is typically integrated with Message Queue servers such as RabbitMQ or Kafka.
Messages are distributed thru these systems from and to various brokers.
A message routing mechanism can be added to MQ server to steer a flow of the messages, if needed.

More theory can be found here: https://en.wikipedia.org/wiki/Message-oriented_middleware


MOM Service
-----------

.. py:currentmodule:: asab.mom.service

.. py:class:: MOMService

Message-oriented middleware is provided by a :py:class:`MOMService` in a :py:mod:`asab.mom` module.

Service initialization and localization example:

.. code:: python

	from asab.mom import Module
	self.add_module(Module)
	svc = self.get_service("asab.MOMService")


Broker
------

.. py:currentmodule:: asab.mom.broker

.. py:class:: Broker

The broker is an object that provides methods for sending and receiving messages.
It is also responsible for a underlaying transport of messages e.g. over the network to other brokers or MQ servers.

A base broker class :py:class:`Broker` cannot be created directly, see available brokers below.
Broker creating example:

.. code:: python

	from asab.mom.amqp import AMQPBroker
	broker = AMQPBroker(app, config_section_name="bsfrgeocode:amqp")

*Note: MOM Service has to be initialized.*


Sending messages
^^^^^^^^^^^^^^^^

.. py:method:: Broker.publish(self, body, target:str='', correlation_id:str=None)

Publish the message to a MQ server.

.. code:: python

	message = "Hello World!"
	await broker.publish(message, target="example")


Receiving messages
^^^^^^^^^^^^^^^^^^

.. py:method:: Broker.subscribe(subscription:str)

Subscribe the broker to a specific subscription (e.g. topic or queue) on the MQ server.
Once completed, messages starts to flow in and they are *routed* based on the target.


.. py:method:: Broker.add(target:str, handler, reply_to:str=None)

A message *handler* must be a coroutine that accept `properties` and `body` of the incoming message.
Incoming messages are routed based on their *target* to a specific handler.
If there is no registered handler for a target, the message is discarted.

.. code:: python

	broker.subscribe("topic")
	broker.add('example', example_handler)

	async def example_handler(self, properties, body):
		print("Recevied", body)



Replying to a message
^^^^^^^^^^^^^^^^^^^^^

Message-oriented middleware is the asynchronous message passing model.
By a mechanism of a message correlation, MOM service allow to reply to a message in the handler.


Example of the handler:

.. code:: python

	async def example_handler(self, properties, body):
		print("Recevied", body)
		return "Hi there too"



Available brokers
^^^^^^^^^^^^^^^^^
.. py:currentmodule:: asab.mom.amqp

.. py:class:: AMQPBroker


