import logging
import asyncio

from .. import Service, Config
from ..metrics.service import MetricsService

from .metrics import LogmanIOMetrics
from .log import LogmanIOLogHandler


L = logging.getLogger(__name__)


class LogManIOService(Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		self.URL = Config.get('logman.io', 'url').format(
			username=Config.get('logman.io', 'username'),
			password=Config.get('logman.io', 'password'),
			virtualhost=Config.get('logman.io', 'virtualhost'),
		)

		self.OutboundQueue = asyncio.Queue(loop=app.Loop)

		from .amqp import LogManIOAMQPUplink as Uplink
		# from .websocket import LogManIOWebSocketUplink as Uplink
		self.Uplink = Uplink(app, self.URL, self.OutboundQueue)


	async def initialize(self, app):
		await super().initialize(app)
		await self.Uplink.initialize(app)


	async def finalize(self, app):
		await self.Uplink.finalize(app)
		await super().finalize(app)


	def configure_metrics(self, metrics_service):
		assert(isinstance(metrics_service, MetricsService))
		metrics_target = LogmanIOMetrics(self)
		metrics_service.add_target(metrics_target)


	def configure_logging(self, app):
		log_handler = LogmanIOLogHandler(self)
		app.Logging.RootLogger.addHandler(log_handler)
