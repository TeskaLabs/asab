import aiohttp
import logging
import json

import asab
from .service import StorageServiceABC

#
L = logging.getLogger(__name__)
#

asab.Config.add_defaults(
	{
		'asab:storage': {
			'elasticsearch_url': 'http://localhost:9200/',  # Can be multi-URL. Each URL should be separated by ';' to a node in ElasticSearch cluster
			'elasticsearch_username': '',
			'elasticsearch_password': '',
			'elasticsearch_loader_per_url': 4,
			'elasticsearch_output_queue_max_size': 10,
			'elasticsearch_bulk_out_max_size': 1024 * 1024,
			'elasticsearch_timeout': 300,
			'elasticsearch_allowed_bulk_response_codes': '200,201,409',
		}
	}
)


class StorageService(StorageServiceABC):
	"""
	Depends on `aiohttp`.
	"""

	def __init__(self, app, service_name, config_section_name='asab:storage'):
		super().__init__(app, service_name)
		self.Loop = app.Loop

		self.ESURL = asab.Config.get(config_section_name, 'elasticsearch_url')
		#self._timeout = asab.Config.get(config_section_name, 'elasticsearch_timeout')

		username = asab.Config.get(config_section_name, 'elasticsearch_username')
		password = asab.Config.get(config_section_name, 'elasticsearch_password')

		if username == '':
			self._auth = None
		else:
			self._auth = aiohttp.BasicAuth(login=username, password=password)
		self.ClientSession = aiohttp.ClientSession(auth=self._auth, loop=self.Loop)

	async def create_update(self, index, _id=None, data=None):
		if _id:
			url = "http://{}{}/_doc/{}".format(self.ESURL, index, _id)
		else:
			url = "http://{}{}/".format(self.ESURL, index)

		async with self.ClientSession.request(method="PUT", url=url, data=json.dumps(data), headers={'Content-Type': 'application/json'}) as resp:
			return await resp.json()

	async def read_item(self, index, _id):
		url = "http://{}{}/_doc/{}".format(self.ESURL, index, _id)
		async with self.ClientSession.request(method="GET", url=url) as resp:
			return resp

	async def delete(self, index, _id=None):
		if _id:
			url = "http://{}{}/_doc/{}".format(self.ESURL, index, _id)
		else:
			url = "http://{}{}".format(self.ESURL, index)
		async with self.ClientSession.request(method="DELETE", url=url) as resp:
			return resp

	async def list_items(self, index, size=10000):
		url = "http://{}{}/_search?size={}".format(self.ESURL, index, size)
		async with self.ClientSession.request(method="GET", url=url) as resp:
			return await resp.json()

	async def list_indices(self, search_string=None):
		url = "http://{}_cat/indices/{}?format=json".format(self.ESURL, search_string)
		resp = await self.ClientSession.request(method="GET", url=url)
		return await resp.json()

	async def get_by(self, collection: str, key: str, value):
		pass
	async def get(self, collection: str, obj_id) -> dict:
		pass
	async def upsertor(self, collection: str, obj_id=None, version: int = 0):
		pass
