import ssl
import time
import logging
import datetime
import urllib.parse
import typing
import contextlib

import aiohttp
import asab

from .service import StorageServiceABC
from .upsertor import UpsertorABC
from ..config import Config
from ..tls import SSLContextBuilder

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'asab:storage': {
			# You may specify multiple ElasticSearch nodes by e.g. http://es01:9200,es02:9200,es03:9200/
			'elasticsearch_url': '',

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

		self.Refresh = Config.get(config_section_name, 'refresh', fallback='true')
		self.ScrollTimeout = Config.get(config_section_name, 'scroll_timeout', fallback='1m')

		# always check if there is a url in the old config section first
		url = Config.getmultiline(config_section_name, 'elasticsearch_url', fallback='')
		if len(url) > 0:
			asab.LogObsolete.warning(
				"Do not configure elasticsearch connection in [asab:storage]. Please use [elasticsearch] section with url, username and password parameters."
			)
		elif len(url) == 0:
			url = asab.Config.getmultiline('elasticsearch', 'url', fallback='')

		self.ServerUrls = get_url_list(url)

		if len(self.ServerUrls) == 0:
			raise RuntimeError("No ElasticSearch URL has been provided.")

		# Authorization: username or API-key
		username = Config.get(config_section_name, 'elasticsearch_username')
		if len(username) == 0:
			username = Config.get('elasticsearch', 'username', fallback='')

		password = Config.get(config_section_name, 'elasticsearch_password')
		if len(password) == 0:
			password = Config.get('elasticsearch', 'password', fallback='')

		api_key = Config.get(config_section_name, 'elasticsearch_api_key')
		if len(api_key) == 0:
			api_key = Config.get('elasticsearch', 'api_key', fallback='')

		# Create headers for requests
		self.Headers = build_headers(username, password, api_key)

		# Build ssl context
		if self.ServerUrls[0].startswith('https://'):
			# check if [asab:storage] section has data for SSL or default to the [elasticsearch] section
			if section_has_ssl_option(config_section_name):
				self.SSLContextBuilder = SSLContextBuilder(config_section_name=config_section_name)
			else:
				self.SSLContextBuilder = SSLContextBuilder(config_section_name='elasticsearch')
			self.SSLContext = self.SSLContextBuilder.build(ssl.PROTOCOL_TLS_CLIENT)
		else:
			self.SSLContext = None


	@contextlib.asynccontextmanager
	async def request(self, method, path, data=None, json=None):
		'''
		This method can be used to do a custom call to ElasticSearch like so:

		async with self.request("GET", "cluster/_health") as resp:
			...

		'''
		async with aiohttp.ClientSession() as session:
			for n, url in enumerate(self.ServerUrls, 1):
				try:
					async with session.request(
						method=method,
						url=url + path,
						ssl=self.SSLContext,
						headers=self.Headers,
						data=data,
						json=json,
					) as resp:

						if resp.status == 401:
							raise ConnectionRefusedError("Response code 401: Unauthorized. Provide authorization by specifying either user name and password or api key.")

						yield resp
						return

				except aiohttp.client_exceptions.ClientConnectorError:
					if n == len(self.ServerUrls):
						raise ConnectionError("Failed to connect to '{}'.".format(url))
					else:
						L.warning("Failed to connect to '{}', iterating to another node".format(url))


	async def is_connected(self) -> bool:
		"""
		Check if the service is connected to ElasticSearch cluster.

		Raises:
			ConnectionError: Connection failed.

		Returns:
			bool: True if the service is connected.
		"""
		async with self.request("GET", "") as resp:
			if resp.status not in {200, 201}:
				resp = await resp.json()
				L.error("Failed to connect to ElasticSearch.", struct_data={
					"code": resp.get("status"),
					"reason": resp.get("error", {}).get("reason")
				})
				return False

			else:
				L.info("Connected to ElasticSearch.", struct_data={"urls": self.ServerUrls})
				return True


	async def get(self, index: str, obj_id: str, decrypt=None) -> dict:
		"""
		Get object by its index and object ID.

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

		async with self.request("GET", "{}/_doc/{}".format(index, obj_id)) as resp:

			if resp.status not in {200, 201}:
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


	async def get_by(self, collection: str, key: str, value, decrypt=None):
		raise NotImplementedError("get_by")

	async def delete(self, index: str, _id=None) -> dict:
		"""
		Delete an entire index or document from that index.

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

		if _id:
			path = "{}/_doc/{}?refresh={}".format(index, _id, self.Refresh)
		else:
			path = "{}".format(index)

		async with self.request("DELETE", path) as resp:
			if resp.status == 404:
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
				return json_response


	async def mapping(self, index: str) -> dict:
		"""
		Retrieve mapping definitions for one index.

		:param index: Specified index.
		:type index: str
		:raise Exception: Connection failed.

		Returns:
			dict: Mapping definitions for the index.
		"""
		async with self.request("GET", "{}/_mapping".format(index)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def get_index_template(self, template_name: str) -> dict:
		"""
		Retrieve ECS Index template for the given template name.

		:param template_name: The name of the ECS template to retrieve.
		:type template_name: str
		:raise Exception: Raised if connection to all server URLs fails.
		:return: ElasticSearch Index template.
		"""
		async with self.request("GET", "_index_template/{}?format=json".format(template_name)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def put_index_template(self, template_name: str, template: dict) -> dict:
		"""
		Create a new ECS index template.

			:param template_name: The name of ECS template.
			:param template: Body for the request.
			:return: JSON response.
			:raise Exception: Raised if connection to all server URLs fails.
		"""
		async with self.request("PUT", "_index_template/{}".format(template_name), json=template) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def reindex(self, previous_index, new_index):

		data = {
			"source": {
				"index": previous_index,
			},
			"dest": {
				"index": new_index,
			}
		}
		async with self.request("POST", "_reindex", json=data) as resp:
			if resp.status != 200:
				raise AssertionError(
					"Unexpected response code when reindexing: {}, {}".format(
						resp.status, await resp.text()
					)
				)

			print('------> REINDEX ;=)')
			return await resp.json()


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

		async with self.request("GET", "{}/_search?size={}&from={}&version=true".format(index, size, _from)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def count(self, index) -> int:
		"""
		Get the number of matches for a given index.

		:param index: The specified index.
		:return: The number of matches for a given index.
		:raise Exception: Connection failed.
		"""

		async with self.request("GET", "{}/_count".format(index)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def indices(self, search_string=None):
		"""
		Return high-level information about indices in a cluster, including backing indices for data streams.

		:param search_string: A search string. Default to None.
		"""

		async with self.request("GET", "_cat/indices/{}?format=json".format(search_string if search_string is not None else "*")) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def empty_index(self, index, settings=None):
		'''
		Create an empty ECS index.
		'''
		# TODO: There is an option here to specify settings (e.g. shard number, replica number etc) and mappings here

		if settings is None:
			settings = {}

		async with self.request("PUT", index, json=settings) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def put_policy(self, policy_name, settings=None):
		'''
		Create a lifecycle policy.
		'''

		if settings is None:
			settings = {}

		async with self.request("PUT", "_ilm/policy/{}".format(policy_name), json=settings) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def policies(self):
		"""
		Return high-level information about ILM policies in a cluster, including backing indices for data streams.

		:param search_string: A search string. Default to None.
		"""
		async with self.request("GET", "_ilm/policy") as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


class ElasticSearchUpsertor(UpsertorABC):

	def __init__(self, storage, collection, obj_id, version=None):
		super().__init__(storage, collection, obj_id, version)

		now = int(time.time())

		self.ModSet['_m'] = now

		if version == 0:
			self.ModSet['_c'] = now  # Set the creation timestamp


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
		async with self.Storage.request(
			"POST",
			"{}/_doc?refresh={}".format(self.Collection, self.Storage.Refresh),
			json=upsert_data,
		) as resp:
			if resp.status not in {200, 201}:
				raise ConnectionError("Unexpected response code: {}".format(resp.status))
			else:
				resp_json = await resp.json()
				self.ObjId = resp_json['_id']
				return self.ObjId


	async def _update_existing_object(self):
		upsert_data = {"doc": {}, "doc_as_upsert": True}

		if len(self.ModSet) == 0:
			return

		for k, v in self.ModSet.items():
			upsert_data["doc"][k] = serialize(self.ModSet[k])

		async with self.Storage.request(
			"POST",
			"{}/_update/{}?refresh={}".format(self.Collection, self.ObjId, self.Storage.Refresh),
			json=upsert_data,
		) as resp:
			if resp.status not in {200, 201}:
				raise ConnectionError("Unexpected response code: {}".format(resp.status))
			else:
				resp_json = await resp.json()
				assert resp_json["result"] == "updated" or resp_json[
					"result"] == "created", "Creating/updating was unsuccessful"
				return self.ObjId


def serialize(v):
	if isinstance(v, datetime.datetime):
		return v.timestamp()
	else:
		return v


def get_url_list(urls):
	server_urls = []
	for url in urls:
		scheme, netloc, path = parse_url(url)

		server_urls += [
			urllib.parse.urlunparse((scheme, netloc, path, None, None, None))
			for netloc in netloc.split(',')
		]

	return server_urls


def parse_url(url):
	parsed_url = urllib.parse.urlparse(url)
	url_path = parsed_url.path
	if not url_path.endswith("/"):
		url_path += "/"

	return parsed_url.scheme, parsed_url.netloc, url_path


def build_headers(username, password, api_key):

	# Check configurations
	if username != '' and username is not None and api_key != '' and api_key is not None:
		raise ValueError("Both username and API key can't be specified. Please choose one option.")

	headers = {
		'Content-Type': 'application/json',
	}

	# Build headers
	if username != '' and username is not None:
		auth = aiohttp.BasicAuth(username, password)
		headers['Authorization'] = auth.encode()

	elif api_key != '' and api_key is not None:
		headers['Authorization'] = 'ApiKey {}'.format(api_key)

	return headers


def section_has_ssl_option(config_section_name):
	"""
	Checks if cert, key, cafile, capath, cadata etc. appears in section's items
	"""
	for item in asab.Config.options(config_section_name):
		if item in SSLContextBuilder.ConfigDefaults:
			return True
	return False
