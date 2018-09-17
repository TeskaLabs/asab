import os
import socket
import uuid
import logging
import time

import asyncio

import asab

import pika
import pika.adapters.asyncio_connection

from ..broker import Broker
from .subscription import QueueSubscriptionObject, ExchangeSubscriptionObject

# from .connection import AMQPConnection
# from .source import AMQPSource, AMQPFullMessageSource
# from .sink import AMQPSink

#

L = logging.getLogger(__name__)

#

class AMQPBroker(Broker):

	'''
The broker that uses Advanced Message Queuing Protocol (AMQP) and it can be used with e.g. RabbitMQ as a message queue.
	'''

	ConfigDefaults = {
		'url': 'amqp://test:test@localhost/test',
		'appname': 'asab.mom',
		'reconnect_delay': 10.0,
		'prefetch_count': 5,

		'exchange': 'amq.fanout',
		'reply_exchange': '',
	}

	def __init__(self, app, accept_replies=False, task_service=None, config_section_name="asab:mom:amqp", config=None):
		super().__init__(app, accept_replies, task_service, config_section_name, config)

		self.Origin = '{}#{}'.format(socket.gethostname(), os.getpid())

		self.Connection = None
		self.SubscriptionObjects = {}
		self.ReplyTo = None

		self.InboundQueue = asyncio.Queue(loop=app.Loop)
		self.OutboundQueue = asyncio.Queue(loop=app.Loop)

		self.SenderFuture = None

		self.Exchange = self.Config['exchange']
		self.ReplyExchange = self.Config['reply_exchange']


	async def finalize(self, app):
		await super().finalize(app)
		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None


	def _reconnect(self):
		if self.Connection is not None:
			if not (self.Connection.is_closing or self.Connection.is_closed):
				self.Connection.close()
			self.Connection = None

		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None

		parameters = pika.URLParameters(self.Config['url'])
		if parameters.client_properties is None:
			parameters.client_properties = dict()
		parameters.client_properties['application'] = self.Config['appname']

		self.SubscriptionObjects.clear()
		self.ReplyTo = None

		self.Connection = pika.adapters.asyncio_connection.AsyncioConnection(
			parameters = parameters,
			on_open_callback=self._on_connection_open,
			on_open_error_callback=self._on_connection_open_error,
			on_close_callback=self._on_connection_close
		)


	# Connection callbacks

	def _on_connection_open(self, connection):
		L.info("AMQP connected")
		asyncio.ensure_future(self.ensure_subscriptions(), loop=self.Loop)
		self.Connection.channel(on_open_callback=self._on_sending_channel_open)

	def _on_connection_close(self, connection, code, reason):
		L.warn("AMQP disconnected ({}): {}".format(code, reason))
		self.Loop.call_later(float(self.Config['reconnect_delay']), self._reconnect)


	def _on_connection_open_error(self, connection, error_message=None):
		L.error("AMQP error: {}".format(error_message if error_message is not None else 'Generic error'))
		self.Loop.call_later(float(self.Config['reconnect_delay']), self._reconnect)


	def _on_sending_channel_open(self, channel):
		self.SenderFuture = asyncio.ensure_future(self._sender_future(channel), loop=self.Loop)


	async def ensure_subscriptions(self):
		if self.Connection is None: return
		if not self.Connection.is_open: return

		for s, pkwargs in self.Subscriptions.items():
			if s in self.SubscriptionObjects: continue
			if pkwargs.get('exchange', False):
				self.SubscriptionObjects[s] = ExchangeSubscriptionObject(self, s, **pkwargs)
			else:
				self.SubscriptionObjects[s] = QueueSubscriptionObject(self, s, **pkwargs)


	async def main(self):
		self._reconnect()
		while True:
			channel, method, properties, body = await self.InboundQueue.get()

			try:
				if self.AcceptReplies and (method.routing_key == self.ReplyTo):
					await self.dispatch("reply", properties, body)
				else:
					await self.dispatch(method.routing_key, properties, body)
			except:
				L.exception("Error when processing inbound message")
				channel.basic_nack(method.delivery_tag, requeue=False)
			else:
				channel.basic_ack(method.delivery_tag)


	async def publish(self,
		body,
		target:str='',
		content_type:str=None,
		content_encoding:str=None,
		correlation_id:str=None,
		reply_to:str=None,
		exchange:str=None
		):
		await self.OutboundQueue.put((
			exchange if exchange is not None else self.Exchange, # Where to publish
			target, # Routing key
			body,
			pika.BasicProperties(
				content_type=content_type,
				content_encoding=content_encoding,
				delivery_mode=1,
				correlation_id=correlation_id,
				reply_to=self.ReplyTo,
				message_id=uuid.uuid4().urn, # id
				app_id=self.Origin, # origin
				#headers = { }
			)
		))


	async def reply(self, body,
		reply_to:str,
		content_type:str=None,
		content_encoding:str=None,
		correlation_id:str=None,
		):
		await self.OutboundQueue.put((
			self.ReplyExchange, # Where to publish
			reply_to, # Routing key
			body,
			pika.BasicProperties(
				content_type=content_type,
				content_encoding=content_encoding,
				delivery_mode=1,
				correlation_id=correlation_id,
				message_id=uuid.uuid4().urn, # id
				app_id=self.Origin, # origin
				#headers = { }
			)
		))


	async def _sender_future(self, channel):
		if self.AcceptReplies:
			self.ReplyTo = await self._create_exclusive_queue(channel, "~R@"+self.Origin)

		while True:
			exchange, routing_key, body, properties = await self.OutboundQueue.get()
			channel.basic_publish(exchange, routing_key, body, properties)


	async def _create_exclusive_queue(self, channel, queue_name):
		lock = asyncio.Event()
		lock.set()

		def on_queue_declared(method):
			lock.clear()
			assert(method.method.queue == queue_name)
			self.SubscriptionObjects[queue_name] = QueueSubscriptionObject(self, queue_name)

		x = channel.queue_declare(
			callback=on_queue_declared,
			queue=queue_name,
			exclusive=True,
			auto_delete=True,
		)

		await lock.wait()

		return queue_name

