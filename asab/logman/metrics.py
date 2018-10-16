import logging
import aiohttp
import platform

import pika

import asab
import asab.metrics.influxdb

#

L = logging.getLogger(__name__)

#

class LogmanIOMetrics(object):


	def __init__(self, svc):
		self.Service = svc
		self.Hostname = platform.node()
		self.Properties = pika.BasicProperties(
			content_type='text/plain',
			delivery_mode=2, # Persistent delivery mode
			headers = {
				'H': self.Hostname,
				'T': 'T',
			}
		)
		self.RoutingKey = asab.Config.get('logman.io', 'routing_key')

	async def process(self, now, mlist):
		body = asab.metrics.influxdb.influxdb_format(now, mlist)
		await self.Service.OutboundQueue.put((self.RoutingKey, body, self.Properties))
