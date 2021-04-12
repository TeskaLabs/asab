import aiohttp
import logging
import datetime
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
			# make the operation visible to search directly, options: true, false, wait_for
			# see: https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html
			'refresh': 'true',
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

		self.Refresh = asab.Config.get(config_section_name, 'refresh')

		if username == '':
			self._auth = None
		else:
			self._auth = aiohttp.BasicAuth(login=username, password=password)

		self._ClientSession = None

	async def finalize(self, app):
		if self._ClientSession is not None and not self._ClientSession.closed:
			await self._ClientSession.close()
			self._ClientSession = None

	def session(self):
		if self._ClientSession is None:
			self._ClientSession = aiohttp.ClientSession(auth=self._auth, loop=self.Loop)
		elif self._ClientSession.closed:
			self._ClientSession = aiohttp.ClientSession(auth=self._auth, loop=self.Loop)
		return self._ClientSession

	async def delete(self, index, _id=None):
		if _id:
			url = "{}{}/_doc/{}?refresh={}".format(self.ESURL, index, _id, self.Refresh)
		else:
			url = "{}{}".format(self.ESURL, index)
		async with self.session().request(method="DELETE", url=url) as resp:
			assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
			resp = await resp.json()
			if resp.get("acknowledged", False):
				return resp
			assert resp["result"] == "deleted", "Document was not deleted"
			return resp

	async def reindex(self, previous_index, new_index):
		if self.ESURL.endswith('/'):
			url = "{}_reindex".format(self.ESURL)
		else:
			url = "{}/_reindex".format(self.ESURL)

		async with self.session().request(
			method="POST",
			url=url,
			headers={"Content-Type": "application/json"},
			data=json.dumps({
				"source": {
					"index": previous_index,
				},
				"dest": {
					"index": new_index,
				}
			})
		) as resp:

			if resp.status != 200:
				raise AssertionError(
					"Unexpected response code when reindexing: {}".format(
						resp.status, await resp.text()
					)
				)

			resp = await resp.json()
			return resp

	async def get_by(self, collection: str, key: str, value):
		raise NotImplementedError("get_by")

	async def get(self, index: str, obj_id) -> dict:
		url = "{}{}/_doc/{}".format(self.ESURL, index, obj_id)
		async with self.session().request(method="GET", url=url) as resp:
			obj = await resp.json()

		# Manipulate the output so that it is a requested object
		ret = obj['_source']
		ret['_v'] = obj['_version']
		ret['_id'] = obj['_id']

		return ret

	def upsertor(self, index: str, obj_id=None, version: int = 0):
		return ElasicSearchUpsertor(self, index, obj_id, version)

	async def list(self, index, _from=0, size=10000, body=None):
		'''
		Custom ElasticSearch method
		'''
		if body is None:
			body = {
				'query': {
					'bool': {
						'must': {
							'match_all': {}
						}
					}
				}
			}
		url = "{}{}/_search?size={}&from={}&version=true".format(self.ESURL, index, size, _from)
		async with self.session().request(method="GET",
		                                  url=url,
		                                  json=body,
		                                  headers={'Content-Type': 'application/json'}
		                                  ) as resp:
			assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
			content = await resp.json()

		return content

	async def count(self, index):
		'''
		Custom ElasticSearch method
		'''

		count_url = "{}{}/_count".format(self.ESURL, index)
		async with self.session().request(method="GET", url=count_url) as resp:
			assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
			total_count = await resp.json()
		return total_count

	async def indices(self, search_string=None):
		'''
		Custom ElasticSearch method
		'''
		url = "{}_cat/indices/{}?format=json".format(self.ESURL, search_string)
		async with self.session().request(method="GET", url=url) as resp:
			assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
			return await resp.json()

	async def empty_index(self, index):
		'''
		Custom ElasticSearch method
		'''
		# TODO: There is an option here to specify settings (e.g. shard number, replica number etc) and mappings here
		url = "{}{}".format(self.ESURL, index)
		async with self.session().request(method="PUT", url=url) as resp:
			assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
			return await resp.json()


class ElasicSearchUpsertor(UpsertorABC):

	@classmethod
	def generate_id(cls):
		raise NotImplementedError("generate_id")

	async def execute(self):
		if self.ObjId is None:
			return await self._insert_noobjid()
		else:
			return await self._upsert()

	async def _insert_noobjid(self):
		setobj = {}

		if self.Version is None:
			self.Version = 0

		if len(self.ModSet) > 0:
			for k, v in self.ModSet.items():
				setobj[k] = serialize(self.ModSet[k])

		if len(self.ModInc) > 0:
			# addobj['$inc'] = self.ModInc
			# raise NotImplementedError("yet")
			pass

		if len(self.ModPush) > 0:
			# addobj['$push'] = {k: {'$each': v} for k, v in self.ModPush.items()}
			raise NotImplementedError("yet")

		# This is insert of the new document, the ObjId is to be generated by the ElasicSearch
		url = "{}{}/_doc?refresh={}".format(
			self.Storage.ESURL, self.Collection, self.Storage.Refresh
		)
		async with self.Storage.session().request(method="POST", url=url, json=setobj) as resp:
			assert resp.status == 201, "Unexpected response code: {}".format(resp.status)
			resp_json = await resp.json()

		self.ObjId = resp_json['_id']

		return self.ObjId

	async def _upsert(self):
		upsertobj = {"doc": {}, "doc_as_upsert": True}

		if len(self.ModSet) > 0:
			for k, v in self.ModSet.items():
				upsertobj["doc"][k] = serialize(self.ModSet[k])
		url = "{}{}/_update/{}?refresh={}".format(self.Storage.ESURL, self.Collection, self.ObjId, self.Storage.Refresh)
		async with self.Storage.session().request(method="POST", url=url, data=json.dumps(upsertobj),
		                                          headers={'Content-Type': 'application/json'}) as resp:
			assert resp.status == 200 or resp.status == 201, "Unexpected response code: {}".format(resp.status)
			resp_json = await resp.json()
			assert resp_json["result"] == "updated" or resp_json[
				"result"] == "created", "Creating/updating was unsuccessful"

		return self.ObjId


def serialize(v):
	if isinstance(v, datetime.datetime):
		return v.timestamp()
	else:
		return v
