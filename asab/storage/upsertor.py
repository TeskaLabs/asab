import abc
import json
import uuid
import hashlib
import datetime
import logging
import aiohttp
import asab.web.rest.json
import typing

#

L = logging.getLogger(__name__)

#


class UpsertorABC(abc.ABC):

	def __init__(self, storage, collection, obj_id, version=None):
		'''
		'''

		self.Storage = storage
		self.Collection = collection
		self.ObjId = obj_id

		self.Version = version

		now = datetime.datetime.now(datetime.timezone.utc)
		self.ModSet = {
			'_m': now,  # Set the modification datetime
		}
		if version == 0:
			self.ModSet['_c'] = now  # Set the creation datetime

		self.ModUnset = {}

		self.ModInc = {
			'_v': 1,  # Increment '_v' at every change
		}

		self.ModPush = {}
		self.ModPull = {}

		self.WebhookResponseData = None


	def get_id_name(self):
		return "_id"


	@classmethod
	def generate_id(cls):
		m = hashlib.sha256()
		m.update(uuid.uuid4().bytes)
		return m.digest()


	def set(self, objField, value, encrypt=False, encrypt_iv=None):
		'''
		Scalar set
		'''
		if encrypt:
			value = self.Storage.aes_encrypt(value, iv=encrypt_iv)
		self.ModSet[objField] = value


	def unset(self, obj_field):
		'''
		Scalar unset
		'''
		self.ModUnset[obj_field] = ""


	def increment(self, field_name, amount=1):
		'''
		Scalar increment
		'''
		self.ModInc[field_name] = amount


	def decrement(self, field_name, amount=1):
		'''
		Scalar decrement
		'''
		return self.increment(field_name, -amount)


	def push(self, field_name, value):
		'''
		Push an item into a list
		'''
		if self.ModPush.get(field_name) is None:
			self.ModPush[field_name] = []
		self.ModPush[field_name].append(value)


	def pull(self, field_name, value):
		'''
		Pull an item from a list
		'''
		if self.ModPull.get(field_name) is None:
			self.ModPull[field_name] = []
		self.ModPull[field_name].append(value)


	@abc.abstractmethod
	async def execute(self, custom_data: typing.Optional[dict] = None):
		"""
		Commit upsertor data to the storage. Afterwards, send a webhook request with upsertion details.

		:custom_data: Custom execution data. Included in webhook payload.

		Example:
			The following upsertion
			```python
			upsertor = storage_service.upsertor("users")
			upsertor.set("name", "Raccoon")
			await upsertor.execute(custom_data={"action": "user_creation"})
			```

			will trigger a webhook whose payload may look like this:
			```json
			{
				"collection": "users",
				"custom": {"action": "user_creation"},
				"upsertor": {
					"id": "2O-h3ulpO-ZwDrkSbQlYB3pYS0JJxCJj3nr6uQAu8aU",
					"id_field_name": "_id",
					"_v": 0,
					"inc": {"_v": 1},
					"set": {
						"_c": "2022-07-11T16:06:04.380445+00:00",
						"_id": "2O-h3ulpO-ZwDrkSbQlYB3pYS0JJxCJj3nr6uQAu8aU",
						"_m": "2022-07-11T16:06:04.380445+00:00",
						"name": "Raccoon"
					}
				}
			}
			```
		"""
		pass


	async def _webhook(self, data: dict):
		assert self.Storage.WebhookURI is not None
		json_dump = asab.web.rest.json.JSONDumper(pretty=False)(data)
		try:
			async with aiohttp.ClientSession(auth=self.Storage.WebhookAuth) as session:
				async with session.put(
					self.Storage.WebhookURI,
					data=json_dump,
					headers={"Content-Type": "application/json"}
				) as response:
					if response.status // 100 != 2:
						text = await response.text()
						L.error("Webhook endpoint responded with {}:\n{}".format(response.status, text))
						return
					self.WebhookResponseData = await response.json()
		except json.decoder.JSONDecodeError as e:
			L.error("Failed to decode JSON response from webhook: {}".format(str(e)))
		except Exception as e:
			L.error("Webhook call failed with {}: {}".format(type(e).__name__, str(e)))
