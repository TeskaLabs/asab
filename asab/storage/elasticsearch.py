import aiohttp
import logging
import json

import asab
from .service import StorageServiceABC
from .upsertor import UpsertorABC

#
L = logging.getLogger(__name__)
#

asab.Config.add_defaults(
	{
		'asab:storage': {
			'elasticsearch_url': 'http://localhost:9200/',
			'elasticsearch_username': '',
			'elasticsearch_password': '',
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
		# self._timeout = asab.Config.get(config_section_name, 'elasticsearch_timeout')

		username = asab.Config.get(config_section_name, 'elasticsearch_username')
		password = asab.Config.get(config_section_name, 'elasticsearch_password')

		if username == '':
			self._auth = None
		else:
			self._auth = aiohttp.BasicAuth(login=username, password=password)
		self.ClientSession = aiohttp.ClientSession(auth=self._auth, loop=self.Loop)


	async def delete(self, index, _id=None):
		if _id:
			url = "{}{}/_doc/{}".format(self.ESURL, index, _id)
		else:
			url = "{}{}".format(self.ESURL, index)
		async with self.ClientSession.request(method="DELETE", url=url) as resp:
			return resp


	async def get_by(self, collection: str, key: str, value):
		raise NotImplementedError("get_by")


	async def get(self, index: str, obj_id) -> dict:
		url = "{}{}/_doc/{}".format(self.ESURL, index, obj_id)
		async with self.ClientSession.request(method="GET", url=url) as resp:
			return resp


	async def upsertor(self, collection: str, obj_id=None, version: int = 0):
		return ElasicSearchUpsertor(self, collection, obj_id, version)


	async def list(self, index, size=10000):
		'''
		Custom ElasticSearch method
		'''
		url = "{}{}/_search?size={}".format(self.ESURL, index, size)
		async with self.ClientSession.request(method="GET", url=url) as resp:
			return await resp.json()


	async def indices(self, search_string=None):
		'''
		Custom ElasticSearch method
		'''
		url = "{}_cat/indices/{}?format=json".format(self.ESURL, search_string)
		resp = await self.ClientSession.request(method="GET", url=url)
		return await resp.json()


class ElasicSearchUpsertor(UpsertorABC):


	@classmethod
	def generate_id(cls):
		return bson.objectid.ObjectId()


	async def execute(self):
		id_name = self.get_id_name()
		addobj = {}


		return self.ObjId
