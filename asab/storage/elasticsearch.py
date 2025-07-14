import ssl
import time
import json
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
			L.error("No ElasticSearch URL has been provided. The application will work without Elasticsearch storage.")
			return

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
		"""
		This method can be used to do a custom call to Elasticsearch like so:

		Usage:
			async with self.request("GET", "cluster/_health") as resp:
			...

		"""
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


	async def is_connected(self) -> bool:
		"""
		Check if the service is connected to Elasticsearch cluster.

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
					"reason": resp.get("error")
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

		async with self.request("GET", "{}/_doc/{}".format(index, urllib.parse.quote(obj_id))) as resp:

			if resp.status not in {200, 201, 404}:
				resp = await resp.json()
				raise ConnectionError("Failed to retrieve data from ElasticSearch. Got {}: {}".format(
					resp.get("status"),
					resp.get("error")
				))

			else:
				obj = await resp.json()

				if not obj.get("found"):
					return None

				ret = obj['_source']
				ret['_v'] = obj['_version']
				ret['_id'] = obj['_id']
				return ret


	async def get_by(self, collection: str, key: str, value, decrypt=None):
		raise NotImplementedError("get_by")


	async def delete(self, index: str, _id=None) -> dict:
		"""
		Delete an entire index or a specific document within the index.

		Args:
			index (str): The name of the index to delete.
			_id (str, optional): The ID of the document to delete. If not provided, the entire index is deleted.

		Returns:
			dict: A response from Elasticsearch indicating the result of the delete operation.

		Raises:
			ConnectionRefusedError: If authorization fails (HTTP 401).
			KeyError: If the document with the specified ID does not exist (HTTP 404).
			ConnectionError: If an unexpected response status is returned from Elasticsearch.
			Exception: If a connection error occurs during the request.
		"""

		if _id:
			path = "{}/_doc/{}?refresh={}".format(index, urllib.parse.quote(_id), self.Refresh)
		else:
			path = "{}".format(index)

		async with self.request("DELETE", path) as resp:
			if resp.status == 404:
				raise KeyError("No existing object with ID {}".format(_id))

			elif resp.status not in {200, 201}:
				resp = await resp.json()
				raise ConnectionError("Failed to retrieve data from ElasticSearch. Got {}: {}".format(
					resp.get("status"),
					resp.get("error", {})
				))

			else:
				json_response = await resp.json()

				if json_response.get("acknowledged", False):
					return json_response
				assert json_response["result"] == "deleted", "Document was not deleted"
				return json_response


	async def mapping(self, index: str) -> dict:
		"""
		Retrieve mapping definitions for a specified index.

		Args:
			index (str): The name of the index.

		Returns:
			dict: Mapping definitions for the specified index.

		Raises:
			Exception: If the request fails.
		"""

		async with self.request("GET", "{}/_mapping".format(index)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def get_index_template(self, template_name: str) -> dict:
		"""
		Retrieve an ECS index template by name.

		Args:
			template_name (str): The name of the ECS template to retrieve.

		Returns:
			dict: The requested ECS index template.

		Raises:
			Exception: If the request fails.
		"""

		async with self.request("GET", "_index_template/{}?format=json".format(template_name)) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))
			return await resp.json()


	async def put_index_template(self, template_name: str, template: dict) -> dict:
		"""
		Create or update an ECS index template.

		Args:
			template_name (str): The name of the ECS template.
			template (dict): The body of the template.

		Returns:
			dict: The response from Elasticsearch.

		Raises:
			Exception: If the request fails.
		"""
		async with self.request("PUT", "_index_template/{}?master_timeout=120s".format(template_name), json=template) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def reindex(self, previous_index, new_index):
		"""
		Reindex documents from one index to another.

		Args:
			previous_index (str): The source index.
			new_index (str): The destination index.

		Returns:
			dict: Response from Elasticsearch reindex API.

		Raises:
			AssertionError: If the request fails.
		"""

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

			return await resp.json()


	def upsertor(self, index: str, obj_id=None, version: int = 0):
		"""
		Create an upsertor object for inserting or updating documents.

		Args:
			index (str): The index where the document will be upserted.
			obj_id (str, optional): The ID of the document. Defaults to None.
			version (int): Document version. Defaults to 0.

		Returns:
			ElasticSearchUpsertor: An instance for performing the upsert operation.
		"""
		return ElasticSearchUpsertor(self, index, obj_id, version)


	async def list(self, index: str, _from: int = 0, size: int = 10000, body: typing.Optional[dict] = None, last_hit_sort=None, _filter=None, sorts=None) -> dict:
		"""
		List documents in an index with support for pagination, filtering, and sorting.

		Args:
			index (str): The name of the index.
			_from (int): Starting document offset. Defaults to 0.
			size (int): Number of hits to return. Defaults to 10000.
			body (Optional[dict]): Custom Elasticsearch query body. If not provided, a default query is constructed.
			last_hit_sort (list, optional): Sort values from the last hit for deep pagination.
			_filter (str, optional): Wildcard filter string.
			sorts (list, optional): List of tuples specifying sort fields and order.

		Returns:
			dict: Search results and sort values for pagination.

		Raises:
			Exception: If the request fails.
		"""

		if body is None and not _filter:
			body = {
				'query': {
					'bool': {
						'must': {
							'match_all': {}
						}
					}
				}
			}

		elif _filter:
			# Apply case-insensitive filtering if _filter is provided
			body = {'query': {}}
			body['query']['wildcard'] = {
				'_keys': {
					'value': f"*{_filter.lower()}*",  # Case-insensitive wildcard search
					'case_insensitive': True  # Requires ES 7.10+
				}
			}

		if sorts:
			body['sort'] = []

			for field, desc in sorts:
				order = 'desc' if desc else 'asc'
				body['sort'].append({field: {"order": order}})

		else:

			# https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#search-after
			body['sort'] = [{'_id': 'asc'}]  # Always need a consistent sort order for deep pagination

		# Use "search_after" for deep pagination when "_from" exceeds 10,000
		if last_hit_sort:
			body['search_after'] = last_hit_sort

		async with self.request("GET", "{}/_search?size={}&from={}&version=true".format(index, size, _from), json=body) as resp:

			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			result = await resp.json()

			last_hit = result['hits']['hits'][-1] if result['hits']['hits'] else None
			last_hit_sort = last_hit['sort'] if last_hit else []

			return result, last_hit_sort


	async def count(self, index, _filter=None) -> int:
		"""
		Count the number of documents in an index with optional filtering.

		Args:
			index (str): The name of the index.
			_filter (Optional[str]): Optional wildcard filter string.

		Returns:
			int: Number of matching documents.

		Raises:
			Exception: If the request fails.
		"""

		if _filter:
			# Apply case-insensitive filtering if _filter is provided
			body = {'query': {}}
			body['query']['wildcard'] = {
				'_keys': {
					'value': f"*{_filter.lower()}*",  # Case-insensitive wildcard search
					'case_insensitive': True  # Requires ES 7.10+
				}
			}

		else:
			body = {}

		async with self.request("GET", "{}/_count".format(index), json=body) as resp:

			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def indices(self, search_string=None):
		"""
		Get a list of all indices in the Elasticsearch cluster.

		Args:
			search_string (Optional[str]): A filter string for index names.

		Returns:
			list: A list of index metadata.

		Raises:
			Exception: If the request fails.
		"""

		async with self.request("GET", "_cat/indices/{}?format=json&s=index".format(search_string if search_string is not None else "*")) as resp:

			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			res = await resp.json()
			return res


	async def empty_index(self, index, settings=None):
		"""
		Create an empty ECS index.

		Args:
			index (str): The name of the index.
			settings (Optional[dict]): Index settings.

		Returns:
			dict: Elasticsearch response.

		Raises:
			Exception: If the request fails.
		"""

		if settings is None:
			settings = {}

		async with self.request("PUT", index, json=settings) as resp:

			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def put_policy(self, policy_name, settings=None):
		"""
		Create a lifecycle policy.

		Args:
			policy_name (str): The name of the ILM policy.
			settings (Optional[dict]): The policy settings.

		Returns:
			dict: Elasticsearch response.

		Raises:
			Exception: If the request fails.
		"""

		if settings is None:
			settings = {}

		async with self.request("PUT", "_ilm/policy/{}?master_timeout=120s".format(policy_name), json=settings) as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def policies(self):
		"""
		Retrieve a list of all ILM lifecycle policies.

		Returns:
			dict: A dictionary of lifecycle policies.

		Raises:
			Exception: If the request fails.
		"""

		async with self.request("GET", "_ilm/policy") as resp:
			if resp.status != 200:
				raise Exception("Unexpected response code: {}: '{}'".format(resp.status, await resp.text()))

			return await resp.json()


	async def update_by_bulk(self, index: str, documents: list) -> dict:
		"""
		Update or insert multiple documents in bulk.

		Args:
			index (str): The name of the index.
			documents (list): A list of dictionaries each with '_id' and '_source'.

		Returns:
			dict: Elasticsearch bulk API response.

		Raises:
			RuntimeError: If the bulk operation fails.
		"""

		if not documents:
			return 0

		# Construct bulk request payload
		bulk_data = ""

		for doc in documents:
			doc_id = doc.get("_id")
			source = doc.get("_source")

			if not doc_id or not source:
				continue  # Skip invalid documents

			bulk_data += json.dumps({"update": {"_index": index, "_id": doc_id}}) + "\n"
			bulk_data += json.dumps({"doc": source, "doc_as_upsert": True}) + "\n"

		async with self.request("POST", "_bulk?refresh={}".format(self.Refresh), data=bulk_data.encode("utf-8")) as resp:

			if resp.status != 200:
				raise RuntimeError(f"Bulk update failed: {resp.status} - {await resp.text()}")

			result = await resp.json()

			# Get how many items were updated
			items_updated = 0

			for item in result.get("items", []):

				for value in item.values():

					if value.get("status") in {200, 201}:
						items_updated += 1

			return items_updated


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
			"{}/_update/{}?refresh={}".format(self.Collection, urllib.parse.quote(self.ObjId), self.Storage.Refresh),
			json=upsert_data,
		) as resp:
			if resp.status not in {200, 201}:
				raise ConnectionError("Unexpected response code: '{}' with response '{}'".format(resp.status, await resp.text()))
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
