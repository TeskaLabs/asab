import logging
import aiohttp
import copy

import asab

#

L = logging.getLogger(__name__)

#


class HTTPTarget(asab.Configurable):

	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name, config)
		self.URL = self.Config.get('url')


	async def process(self, metrics, now):
		metrics_to_send = copy.deepcopy(metrics)
		try:
			async with aiohttp.ClientSession() as session:
				async with session.post(self.URL, json=metrics_to_send) as resp:
					response = await resp.text()
					if resp.status != 200:
						L.warning(
							"HTTP metrics target rejected the metrics write request.",
							struct_data={
								"url": self.URL,
								"status": resp.status,
								"response": response,
							},
						)
		except aiohttp.client_exceptions.ClientConnectorError:
			L.error(
				"Cannot reach HTTP metrics target; metrics were not delivered.",
				struct_data={"url": self.URL},
			)
		except Exception:
			L.exception(
				"Unexpected error while sending metrics to HTTP target.",
				struct_data={"url": self.URL},
			)
