import time
import json
import aiohttp
import logging
import datetime
import urllib.parse
import typing

from .service import StorageServiceABC
from .upsertor import UpsertorABC
from ..config import Config

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'asab:storage': {
			# You may specify multiple ElasticSearch nodes by e.g. http://es01:9200,es02:9200,es03:9200/
			'elasticsearch_url': 'http://localhost:9200/',

			'elasticsearch_username': '',
			'elasticsearch_password': '',

			# make the operation visible to search directly, options: true, false, wait_for
			# see: https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html
			'refresh': 'true',
			'scroll_timeout': '1m',
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

		self.URL = Config.get(config_section_name, 'elasticsearch_url')
		parsed_url = urllib.parse.urlparse(self.URL)
		self.ServerUrls = [
			urllib.parse.urlunparse((parsed_url.scheme, netloc, parsed_url.path, None, None, None))
			for netloc in parsed_url.netloc.split(',')
		]

		self.Refresh = Config.get(config_section_name, 'refresh')
		self.ScrollTimeout = Config.get(config_section_name, 'scroll_timeout')

		username = Config.get(config_section_name, 'elasticsearch_username')
		if username == '':
			self._auth = None
		else:
			password = Config.get(config_section_name, 'elasticsearch_password')
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
		for url in self.ServerUrls:
			try:
				if _id:
					url = "{}{}/_doc/{}?refresh={}".format(url, index, _id, self.Refresh)
				else:
					url = "{}{}".format(url, index)
				async with self.session().request(method="DELETE", url=url) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					resp = await resp.json()

					if resp.get("acknowledged", False):
						return resp
					assert resp["result"] == "deleted", "Document was not deleted"
					return resp
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def reindex(self, previous_index, new_index):
		for url in self.ServerUrls:
			try:
				if url.endswith('/'):
					url = "{}_reindex".format(url)
				else:
					url = "{}/_reindex".format(url)

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
							"Unexpected response code when reindexing: {}, {}".format(
								resp.status, await resp.text()
							)
						)
					resp = await resp.json()
					return resp
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def get_by(self, collection: str, key: str, value, decrypt=None):
		raise NotImplementedError("get_by")


	async def mapping(self, index: str) -> dict:
		for url in self.ServerUrls:
			url = "{}{}/_mapping".format(url, index)
			try:
				async with self.session().request(method="GET", url=url) as resp:
					obj = await resp.json()
					return obj
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def get(self, index: str, obj_id, decrypt=None) -> dict:
		if decrypt is not None:
			raise NotImplementedError("AES encryption for ElasticSearch not implemented")

		for url in self.ServerUrls:
			url = "{}{}/_doc/{}".format(url, index, obj_id)
			try:
				async with self.session().request(method="GET", url=url) as resp:
					obj = await resp.json()
					ret = obj['_source']
					ret['_v'] = obj['_version']
					ret['_id'] = obj['_id']
					return ret
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def get_index_template(self, template_name) -> dict:
		for url in self.ServerUrls:
			url = "{}_template/{}?format=json".format(url, template_name)
			try:
				async with self.session().request(method="GET", url=url, headers={
					'Content-Type': 'application/json'
				}) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					content = await resp.json()
					return content
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def put_index_template(self, template_name, template):
		for url in self.ServerUrls:
			url = "{}_template/{}?include_type_name".format(url, template_name)
			try:
				async with self.session().request(method="POST", url=url, data=json.dumps(template), headers={
					'Content-Type': 'application/json'
				}) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					resp = await resp.json()
					return resp
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def scroll(self, index: str, body=None):
		if body is None:
			body = {
				"query": {"bool": {"must": {"match_all": {}}}}
			}

		scroll_id = None
		while True:
			for url in self.ServerUrls:
				if scroll_id is None:
					path = "{}/_search?scroll={}".format(
						index, self.ScrollTimeout
					)
					request_body = body
				else:
					path = "_search/scroll"
					request_body = {
						"scroll": self.ScrollTimeout,
						"scroll_id": scroll_id,
					}
				url = "{}{}".format(url, path)
				try:
					async with self.session().request(
						method="POST",
						url=url,
						json=request_body,
						headers={
							"Content-Type": "application/json"
						},
					) as resp:
						if resp.status != 200:
							data = await resp.text()
							L.error(
								"Failed to fetch data from ElasticSearch: {} from {}\n{}".format(
									resp.status, url, data
								)
							)
							break
						response_json = await resp.json()
				except aiohttp.client_exceptions.ClientConnectorError:
					if url == self.Storage.ServerUrls[-1]:
						raise Exception(
							"Failed to connect to '{}'".format(
								url
							)
						)
					else:
						L.warning(
							"Failed to connect to '{}', iterating to another cluster node".format(
								url
							)
						)

			scroll_id = response_json.get("_scroll_id")
			if scroll_id is None:
				break
			return response_json

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
		for url in self.ServerUrls:
			try:
				url = "{}{}/_search?size={}&from={}&version=true".format(url, index, size, _from)
				async with self.session().request(
					method="GET",
					url=url,
					json=body,
					headers={'Content-Type': 'application/json'}
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					content = await resp.json()
					return content
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def count(self, index):
		'''
		Custom ElasticSearch method
		'''
		for url in self.ServerUrls:
			try:
				count_url = "{}{}/_count".format(url, index)
				async with self.session().request(method="GET", url=count_url) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					total_count = await resp.json()
					return total_count
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def indices(self, search_string=None):
		'''
		Custom ElasticSearch method
		'''
		for url in self.ServerUrls:
			try:
				url = "{}_cat/indices/{}?format=json".format(url, search_string if search_string is not None else "*")
				async with self.session().request(method="GET", url=url) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					return await resp.json()

			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def empty_index(self, index):
		'''
		Custom ElasticSearch method
		'''
		# TODO: There is an option here to specify settings (e.g. shard number, replica number etc) and mappings here
		for url in self.ServerUrls:
			try:
				url = "{}{}".format(url, index)
				async with self.session().request(method="PUT", url=url) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					return await resp.json()
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


class ElasicSearchUpsertor(UpsertorABC):

	def __init__(self, storage, collection, obj_id, version=None):
		super().__init__(storage, collection, obj_id, version)

		now = int(time.time())

		self.ModSet['_m'] = now

		if version == 0:
			self.ModSet['_c'] = now  # Set the creation timestamp


	@classmethod
	def generate_id(cls):
		raise NotImplementedError("generate_id")


	async def execute(self, custom_data: typing.Optional[dict] = None):
		# TODO: Implement webhook call
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
		for url in self.Storage.ServerUrls:
			url = "{}{}/_doc?refresh={}".format(
				url, self.Collection, self.Storage.Refresh
			)

			try:
				async with self.Storage.session().request(method="POST", url=url, json=setobj) as resp:
					if resp.status != 201:
						raise RuntimeError("Unexpected response code: {}".format(resp.status))

					resp_json = await resp.json()
					self.ObjId = resp_json['_id']
					return self.ObjId

			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def _upsert(self):
		upsertobj = {"doc": {}, "doc_as_upsert": True}

		if len(self.ModSet) > 0:
			for k, v in self.ModSet.items():
				upsertobj["doc"][k] = serialize(self.ModSet[k])

			for url in self.Storage.ServerUrls:
				try:
					url = "{}{}/_update/{}?refresh={}".format(url, self.Collection, self.ObjId, self.Storage.Refresh)
					async with self.Storage.session().request(method="POST", url=url, data=json.dumps(upsertobj),
																headers={'Content-Type': 'application/json'}) as resp:
						assert resp.status == 200 or resp.status == 201, "Unexpected response code: {}".format(resp.status)
						resp_json = await resp.json()
						assert resp_json["result"] == "updated" or resp_json[
							"result"] == "created", "Creating/updating was unsuccessful"
						return self.ObjId
				except aiohttp.client_exceptions.ClientConnectorError:
					if url == self.Storage.ServerUrls[-1]:
						raise Exception("Failed to connect to '{}'".format(url))
					else:
						L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


def serialize(v):
	if isinstance(v, datetime.datetime):
		return v.timestamp()
	else:
		return v
