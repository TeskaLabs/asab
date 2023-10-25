import time
import json
import aiohttp
import aiohttp.client_exceptions
import logging
import datetime
import urllib.parse
import typing
import asyncio

from .service import StorageServiceABC
from .upsertor import UpsertorABC
from ..config import Config
from ..tls import SSLContextBuilder

import ssl

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
			'elasticsearch_api_key': '',

			# make the operation visible to search directly, options: true, false, wait_for
			# see: https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html
			'refresh': 'true',
			'scroll_timeout': '1m',

			# For SSL options such as `cafile`, please refer to tls.py
		}
	}
)



class StorageService(StorageServiceABC):
	"""
	StorageService for Elastic Search. Depends on `aiohttp` library.
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

		# Authorization: username or API-key
		username = Config.get(config_section_name, 'elasticsearch_username')
		api_key = Config.get(config_section_name, 'elasticsearch_api_key')

		if username != '' and api_key != '':
			L.warning("Both username and API key specified. ES Storage service may not function properly. Please choose one option.")

		if username == '':
			self._auth = None
		else:
			password = Config.get(config_section_name, 'elasticsearch_password')
			self._auth = aiohttp.BasicAuth(login=username, password=password)

		self._ClientSession = None

		# Create headers for requests
		self.Headers = {'Content-Type': 'application/json'}
		if api_key != '':
			self.Headers['Authorization'] = "ApiKey {}".format(api_key)

		self.SSLContextBuilder = SSLContextBuilder(config_section_name)


	async def finalize(self, app):
		"""
		Close the current client session.
		"""
		if self._ClientSession is not None and not self._ClientSession.closed:
			await self._ClientSession.close()
			self._ClientSession = None


	def session(self):
		"""
		Get the current client session.
		"""
		if self._ClientSession is None:
			self._ClientSession = aiohttp.ClientSession(auth=self._auth)
		elif self._ClientSession.closed:
			self._ClientSession = aiohttp.ClientSession(auth=self._auth)
		return self._ClientSession


	async def is_connected(self) -> bool:
		"""Check if the service is connected to ElasticSearch cluster.

		Raises:
			ConnectionError: Connection failed.

		Returns:
			bool: True if the service is connected.
		"""
		for url in self.ServerUrls:

			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				async with self.session().request(
					method="GET",
					url=url,
					ssl=ssl_context,
					headers=self.Headers,
				) as resp:
					await self.session().close()
					if resp.status not in {200, 201}:
						resp = await resp.json()
						L.error("Failed to connect to ElasticSearch.", struct_data={
							"code": resp.get("status"),
							"reason": resp.get("error", {}).get("reason")
						})
						return False

			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise ConnectionError("Failed to connect to '{}'.".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

		L.info("Connected to ElasticSearch.", struct_data={"urls": self.ServerUrls})
		return True


	async def get(self, index: str, obj_id: str, decrypt=None) -> dict:
		"""Get object by its index and object ID.

		Args:
			index (str): Index for the query.
			obj_id (str): ID of the object.
			decrypt (None): Not implemented yet. Defaults to None.

		Raises:
			NotImplementedError: Encryption and decryption has not yet been implemented for ECS.
			ConnectionError: Connection failed.
			ConnectionRefusedError: Authorization required.
			KeyError: Object with the ID does not exist.

		Returns:
			The query result.
		"""
		if decrypt is not None:
			raise NotImplementedError("AES encryption for ElasticSearch not implemented")
		for url in self.ServerUrls:
			request_url = "{}{}/_doc/{}".format(url, index, obj_id)
			try:

				if url.startswith('https://'):
					ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
				else:
					ssl_context = None

				async with self.session().request(
					method="GET",
					url=request_url,
					ssl=ssl_context,
					headers=self.Headers,
				) as resp:
					if resp.status == 401:
						raise ConnectionRefusedError("Response code 401: Unauthorized. Provide authorization by specifying either user name and password or api key.")
					elif resp.status not in {200, 201}:
						resp = await resp.json()
						raise ConnectionError("Failed to retrieve data from ElasticSearch. Got {}: {}".format(
							resp.get("status"),
							resp.get("error", {}).get("reason")
						))
					else:
						obj = await resp.json()
						if not obj.get("found"):
							raise KeyError("No existing object with ID {}".format(obj_id))
						ret = obj['_source']
						ret['_v'] = obj['_version']
						ret['_id'] = obj['_id']
						return ret
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise ConnectionError("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def get_by(self, collection: str, key: str, value, decrypt=None):
		raise NotImplementedError("get_by")

	async def delete(self, index: str, _id=None) -> dict:
		"""Delete an entire index or document from that index.

		Args:
			index: Index to delete.
			_id: If specified, only document with the ID is deleted.

		Raises:
			ConnectionRefusedError: Authorization required (status 401)
			KeyError: No existing object with ID
			ConnectionError: Unexpected status code
			Exception: ClientConnectorError

		Returns:
			The deleted document or message that the entire index was deleted.
		"""
		for url in self.ServerUrls:
			try:
				if _id:
					request_url = "{}{}/_doc/{}?refresh={}".format(url, index, _id, self.Refresh)
				else:
					request_url = "{}{}".format(url, index)

				if url.startswith('https://'):
					ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
				else:
					ssl_context = None

				async with self.session().request(
					method="DELETE",
					url=request_url,
					ssl=ssl_context,
					headers=self.Headers
				) as resp:
					if resp.status == 401:
						raise ConnectionRefusedError("Response code 401: Unauthorized. Provide authorization by specifying either user name and password or api key.")
					elif resp.status == 404:
						raise KeyError("No existing object with ID {}".format(_id))
					elif resp.status not in {200, 201}:
						raise ConnectionError("Failed to retrieve data from ElasticSearch. Got {}: {}".format(
							resp.get("status"),
							resp.get("error", {}).get("reason")
						))
					else:
						json_response = await resp.json()

						if json_response.get("acknowledged", False):
							return json_response
						assert json_response["result"] == "deleted", "Document was not deleted"
						await self.session().close()
						return json_response
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def mapping(self, index: str) -> dict:
		"""Retrieve mapping definitions for one index.

		:param index: Specified index.
		:type index: str
		:raise Exception: Connection failed.

		Returns:
			dict: Mapping definitions for the index.
		"""
		for url in self.ServerUrls:
			request_url = "{}{}/_mapping".format(url, index)

			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				async with self.session().request(
					method="GET",
					url=request_url,
					ssl=ssl_context,
					headers=self.Headers
				) as resp:
					obj = await resp.json()
					await self.session().close()
					return obj
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise ConnectionError("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def get_index_template(self, template_name: str) -> dict:
		"""Retrieve ECS Index template for the given template name.

		:param template_name: The name of the ECS template to retrieve.
		:type template_name: str
		:raise Exception: Raised if connection to all server URLs fails.
		:return: ElasticSearch Index template.
		"""
		for url in self.ServerUrls:
			request_url = "{}_template/{}?format=json".format(url, template_name)

			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				async with self.session().request(
					method="GET",
					url=request_url,
					headers=self.Headers,
					ssl=ssl_context,
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					content = await resp.json()
					await self.session().close()
					return content
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def put_index_template(self, template_name: str, template: dict) -> dict:
		"""Create a new ECS index template.

			:param template_name: The name of ECS template.
			:param template: Body for the request.
			:return: JSON response.
			:raise Exception: Raised if connection to all server URLs fails.
		"""
		for url in self.ServerUrls:
			request_url = "{}_template/{}".format(url, template_name)
			L.warning("Posting index template into url: {}".format(request_url))

			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				async with self.session().request(
					method="POST",
					url=request_url,
					data=json.dumps(template),
					headers=self.Headers,
					ssl=ssl_context,
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					resp = await resp.json()
					await self.session().close()
					return resp
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))
					return {}


	async def reindex(self, previous_index, new_index):
		for url in self.ServerUrls:
			try:
				if url.endswith('/'):
					request_url = "{}_reindex".format(url)
				else:
					request_url = "{}/_reindex".format(url)

				if url.startswith('https://'):
					ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
				else:
					ssl_context = None

				async with self.session().request(
					method="POST",
					url=request_url,
					headers=self.Headers,
					ssl=ssl_context,
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
					await self.session().close()
					return resp
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise ConnectionError("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def scroll(self, index: str, body: typing.Optional[dict] = None) -> dict:
		"""Retrieve the next batch of results for a scrolling search.

		:param index: The index name.
		:type index: str
		:param body: Custom body for the request. Defaults to None.
		:type body: dict
		:return: JSON response.
		:raise Exception: Raised if connection to all server URLs fails.
		"""
		if body is None:
			body = {
				"query": {"bool": {"must": {"match_all": {}}}}
			}

		scroll_id = None
		while True:
			for url in self.ServerUrls:

				if url.startswith('https://'):
					ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
				else:
					ssl_context = None

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
				request_url = "{}{}".format(url, path)
				try:
					async with self.session().request(
						method="POST",
						url=request_url,
						json=request_body,
						headers=self.Headers,
						ssl=ssl_context,
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
						await self.session().close()
				except aiohttp.client_exceptions.ClientConnectorError:
					if url == self.ServerUrls[-1]:
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
		return ElasticSearchUpsertor(self, index, obj_id, version)


	async def list(self, index: str, _from: int = 0, size: int = 10000, body: typing.Optional[dict] = None) -> dict:
		"""List data matching the index.

		:param index: Specified index.
		:param _from:  Starting document offset. Defaults to 0.
		:type _from: int
		:param size: The number of hits to return. Defaults to 10000.
		:type size: int
		:param body: An optional request body. Defaults to None.
		:type body: dict

		:return: The query search result.
		:raise Exception: Raised if connection to all server URLs fails.

		"""
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

			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				request_url = "{}{}/_search?size={}&from={}&version=true".format(url, index, size, _from)
				async with self.session().request(
					method="GET",
					url=request_url,
					json=body,
					headers=self.Headers,
					ssl=ssl_context,
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					content = await resp.json()
					return content
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def count(self, index) -> int:
		"""
		Get the number of matches for a given index.

		:param index: The specified index.
		:return: The number of matches for a given index.
		:raise Exception: Connection failed.
		"""
		for url in self.ServerUrls:
			try:
				count_url = "{}{}/_count".format(url, index)
				if url.startswith('https://'):
					ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
				else:
					ssl_context = None

				async with self.session().request(
					method="GET",
					url=count_url,
					ssl=ssl_context,
					headers=self.Headers
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					total_count = await resp.json()
					return total_count
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

	async def indices(self, search_string=None):
		"""
		Return high-level information about indices in a cluster, including backing indices for data streams.

		:param search_string: A search string. Default to None.
		"""
		for url in self.ServerUrls:
			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				request_url = "{}_cat/indices/{}?format=json".format(url, search_string if search_string is not None else "*")
				async with self.session().request(
					method="GET",
					url=request_url,
					ssl=ssl_context,
					headers=self.Headers
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					return await resp.json()

			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


	async def empty_index(self, index):
		'''
		Create an empty ECS index.
		'''
		# TODO: There is an option here to specify settings (e.g. shard number, replica number etc) and mappings here
		for url in self.ServerUrls:
			if url.startswith('https://'):
				ssl_context = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				request_url = "{}{}".format(url, index)
				async with self.session().request(
					method="PUT",
					url=request_url,
					ssl=ssl_context,
					headers=self.Headers
				) as resp:
					assert resp.status == 200, "Unexpected response code: {}".format(resp.status)
					return await resp.json()
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))


class ElasticSearchUpsertor(UpsertorABC):

	def __init__(self, storage, collection, obj_id, version=None):
		super().__init__(storage, collection, obj_id, version)

		now = int(time.time())

		self.ModSet['_m'] = now

		if version == 0:
			self.ModSet['_c'] = now  # Set the creation timestamp

		api_key = Config.get('asab:storage', 'elasticsearch_api_key')
		self.Headers = {'Content-Type': 'application/json'}
		if api_key != '':
			self.Headers['Authorization'] = "ApiKey {}".format(api_key)


	@classmethod
	def generate_id(cls):
		raise NotImplementedError("generate_id")


	async def execute(self, custom_data: typing.Optional[dict] = None, event_type: typing.Optional[str] = None):
		# TODO: Implement webhook call
		if self.ObjId is None:
			return await self._insert_new_object()
		else:
			return await self._update_existing_object()


	async def _insert_new_object(self):
		upsert_data = {}

		if self.Version is None:
			self.Version = 0

		if len(self.ModSet) > 0:
			for k, v in self.ModSet.items():
				upsert_data[k] = serialize(self.ModSet[k])

		if len(self.ModInc) > 0:
			# addobj['$inc'] = self.ModInc
			# raise NotImplementedError("yet")
			pass

		if len(self.ModPush) > 0:
			# addobj['$push'] = {k: {'$each': v} for k, v in self.ModPush.items()}
			raise NotImplementedError("yet")

		# This is insert of the new document, the ObjId is to be generated by the ElasicSearch
		for url in self.Storage.ServerUrls:
			request_url = "{}{}/_doc?refresh={}".format(
				url, self.Collection, self.Storage.Refresh
			)

			if url.startswith('https://'):
				ssl_context = self.Storage.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				async with self.Storage.session().request(
					method="POST",
					url=request_url,
					headers=self.Headers,
					json=upsert_data,
					ssl=ssl_context
				) as resp:
					if resp.status == 401:
						raise ConnectionRefusedError("Response code 401: Unauthorized. Provide authorization by specifying either user name and password or api key.")
					elif resp.status not in {200, 201}:
						raise ConnectionError("Unexpected response code: {}".format(resp.status))
					else:
						resp_json = await resp.json()
						self.ObjId = resp_json['_id']
						await self.Storage.session().close()
						return self.ObjId

			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

			except aiohttp.client_exceptions.ServerDisconnectedError:
				raise Exception("Failed to connect to '{}'".format(url))

			except ValueError as err:
				raise ConnectionError("Both username and API key specified. Please choose one option. {}".format(err))

			# except Exception:
			# 	raise Exception("Failed to connect to '{}'".format(url))

	async def _update_existing_object(self):
		upsert_data = {"doc": {}, "doc_as_upsert": True}

		if len(self.ModSet) > 0:
			for k, v in self.ModSet.items():
				upsert_data["doc"][k] = serialize(self.ModSet[k])

		for url in self.Storage.ServerUrls:
			if url.startswith('https://'):
				ssl_context = self.Storage.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
			else:
				ssl_context = None

			try:
				request_url = "{}{}/_update/{}?refresh={}".format(url, self.Collection, self.ObjId, self.Storage.Refresh)
				async with self.Storage.session().request(
					method="POST",
					url=request_url,
					json=upsert_data,
					headers=self.Headers,
					ssl=ssl_context,
					timeout=30  # Set the timeout to 30 seconds
				) as resp:
					if resp.status == 401:
						raise ConnectionRefusedError(
							"Response code 401: Unauthorized. Provide authorization by specifying either user name and password or api key.")
					elif resp.status not in {200, 201}:
						raise ConnectionError("Unexpected response code: {}".format(resp.status))
					else:
						resp_json = await resp.json()
						assert resp_json["result"] == "updated" or resp_json[
							"result"] == "created", "Creating/updating was unsuccessful"
						await self.Storage.session().close()
						return self.ObjId
			except aiohttp.client_exceptions.ClientConnectorError:
				if url == self.Storage.ServerUrls[-1]:
					raise Exception("Failed to connect to '{}'".format(url))
				else:
					L.warning("Failed to connect to '{}', iterating to another cluster node".format(url))

			except aiohttp.client_exceptions.ServerDisconnectedError:
				raise Exception("Failed to connect to '{}'".format(url))

			except asyncio.TimeoutError:
				raise Exception("Request to '{}' timed out.".format(url))


def serialize(v):
	if isinstance(v, datetime.datetime):
		return v.timestamp()
	else:
		return v
