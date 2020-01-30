import logging

from ..metrics.influxdb import influxdb_format


L = logging.getLogger(__name__)


class LogmanIOMetrics(object):


	def __init__(self, svc):
		self.Service = svc

	async def process(self, now, mlist):
		body = influxdb_format(now, mlist)
		await self.Service.OutboundQueue.put(('T', body))
