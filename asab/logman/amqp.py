import asyncio
import logging
import platform

import pika
import pika.adapters.asyncio_connection

from .. import Config


L = logging.getLogger(__name__)


class LogManIOAMQPUplink(object):


	def __init__(self, app, url, queue):
		self.App = app
		self.OutboundQueue = queue

		self.Parameters = pika.URLParameters(url)
		if self.Parameters.client_properties is None:
			self.Parameters.client_properties = dict()
		self.Parameters.client_properties['application'] = 'asab.logman'

		self.SenderFuture = None
		self.Connection = None

		self.RoutingKey = Config.get('logman.io', 'routing_key')
		self.Hostname = platform.node()


	async def initialize(self, app):
		self._reconnect()


	async def finalize(self, app):
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

		self.Connection = pika.adapters.asyncio_connection.AsyncioConnection(
			parameters=self.Parameters,
			on_open_callback=self._on_connection_open,
			on_open_error_callback=self._on_connection_open_error,
			on_close_callback=self._on_connection_close
		)


	def _on_connection_open(self, connection):
		L.info("LogMan.io connected")

		def _on_sending_channel_open(channel):
			self.SenderFuture = asyncio.ensure_future(self._sender_future(channel), loop=self.App.Loop)

		self.Connection.channel(on_open_callback=_on_sending_channel_open)


	def _on_connection_close(self, connection, *args):
		try:
			code, reason = args
			L.warning("LogMan.io disconnected ({}): {}".format(code, reason))
		except ValueError:
			error, = args
			L.warning("LogMan.io disconnected: {}".format(error))
		self.App.Loop.call_later(30, self._reconnect)


	def _on_connection_open_error(self, connection, error_message=None):
		L.error("LogMan.io error: {}".format(error_message if error_message is not None else 'Generic error'))
		self.App.Loop.call_later(30.0, self._reconnect)


	async def _sender_future(self, channel):
		while True:
			msg_type, body = await self.OutboundQueue.get()
			properties = pika.BasicProperties(
				content_type='application/json' if msg_type == 'sj' else 'text/plain',
				delivery_mode=2,  # Persistent delivery mode
				headers={
					'H': self.Hostname,
					'T': msg_type,
				}
			)

			channel.basic_publish('i', self.RoutingKey, body, properties)
