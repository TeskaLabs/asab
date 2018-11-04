import logging
import asyncio

import asab
import asab.metrics.service

import pika
import pika.adapters.asyncio_connection

from .metrics import LogmanIOMetrics
from .log import LogmanIOLogHandler

#

L = logging.getLogger(__name__)

#

class LogManIOService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.URL = asab.Config.get('logman.io', 'url').format(
			username = asab.Config.get('logman.io', 'username'),
			password = asab.Config.get('logman.io', 'password'),
			virtualhost = asab.Config.get('logman.io', 'virtualhost'),
		)

		self.Connection = None
		self.SenderFuture = None
		self.OutboundQueue = asyncio.Queue(loop=app.Loop)


	async def initialize(self, app):
		self._reconnect()


	async def finalize(self, app):
		await super().finalize(app)
		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None


	def configure_metrics(self, metrics_service):
		assert(isinstance(metrics_service, asab.metrics.service.MetricsService))
		metrics_target = LogmanIOMetrics(self)
		metrics_service.add_target(metrics_target)


	def configure_logging(self, app):
		log_handler = LogmanIOLogHandler(self)
		app.Logging.RootLogger.addHandler(log_handler)


	def _reconnect(self):
		if self.Connection is not None:
			if not (self.Connection.is_closing or self.Connection.is_closed):
				self.Connection.close()
			self.Connection = None

		if self.SenderFuture is not None:
			self.SenderFuture.cancel()
			self.SenderFuture = None

		parameters = pika.URLParameters(self.URL)
		if parameters.client_properties is None:
			parameters.client_properties = dict()
		parameters.client_properties['application'] = 'asab.logman'

		self.Connection = pika.adapters.asyncio_connection.AsyncioConnection(
			parameters = parameters,
			on_open_callback=self._on_connection_open,
			on_open_error_callback=self._on_connection_open_error,
			on_close_callback=self._on_connection_close
		)


	def _on_connection_open(self, connection):
		L.info("LogMan.io connected")

		def _on_sending_channel_open(channel):
			self.SenderFuture = asyncio.ensure_future(self._sender_future(channel), loop=self.App.Loop)

		self.Connection.channel(on_open_callback=_on_sending_channel_open)


	def _on_connection_close(self, connection, code, reason):
		L.warn("LogMan.io disconnected ({}): {}".format(code, reason))
		self.App.Loop.call_later(30, self._reconnect)


	def _on_connection_open_error(self, connection, error_message=None):
		L.error("LogMan.io error: {}".format(error_message if error_message is not None else 'Generic error'))
		self.App.Loop.call_later(30.0, self._reconnect)


	async def _sender_future(self, channel):
		while True:
			routing_key, body, properties = await self.OutboundQueue.get()
			channel.basic_publish('i', routing_key, body, properties)
