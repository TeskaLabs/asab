import datetime
import typing
import motor.motor_asyncio
import pymongo
import bson

import asab
from .exceptions import DuplicateError
from .service import StorageServiceABC
from .upsertor import UpsertorABC

asab.Config.add_defaults(
	{
		'asab:storage': {
			'mongodb_uri': 'mongodb://localhost:27017',
			'mongodb_database': 'asabdb',
		}
	}
)


class StorageService(StorageServiceABC):
	'''
	Depends on `pymongo` and `motor`.
	'''


	def __init__(self, app, service_name, config_section_name='asab:storage'):
		super().__init__(app, service_name)
		self.Client = motor.motor_asyncio.AsyncIOMotorClient(asab.Config.get(config_section_name, 'mongodb_uri'))

		self.Database = self.Client.get_database(
			asab.Config.get(config_section_name, 'mongodb_database'),
			codec_options=bson.codec_options.CodecOptions(tz_aware=True, tzinfo=datetime.timezone.utc),
		)
		assert self.Database is not None


	def upsertor(self, collection: str, obj_id=None, version=0):
		return MongoDBUpsertor(self, collection, obj_id, version)


	async def get(self, collection: str, obj_id, decrypt=None) -> dict:
		coll = self.Database[collection]
		ret = await coll.find_one({'_id': obj_id})
		if ret is None:
			raise KeyError("NOT-FOUND")
		if decrypt is not None:
			for field in decrypt:
				if field in ret:
					ret[field] = self.aes_decrypt(ret[field])
		return ret


	async def get_by(self, collection: str, key: str, value, decrypt=None) -> dict:
		"""
		Get object from collection by its key/value

		:param collection: Collection to get from
		:param key: Key to filter on
		:param value: Value to filter on
		:param decrypt: Set of fields to decrypt
		:return: The object retrieved from a storage

		Raises:
			KeyError: If object{key: value} not found in `collection`
		"""
		coll = self.Database[collection]
		ret = await coll.find_one({key: value})
		if ret is None:
			raise KeyError("NOT-FOUND")
		if decrypt is not None:
			for field in decrypt:
				if field in ret:
					ret[field] = self.aes_decrypt(ret[field])
		return ret


	async def collection(self, collection: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
		"""
		Get collection. Useful for custom operations

		:param collection: Collection to get
		:return: AsyncIOMotorCollection

		Examples:

			>>> coll = await storage.collection("test-collection")
			>>> cursor = coll.find({})
			>>> while await cursor.fetch_next:
			... 	obj = cursor.next_object()
			... 	pprint.pprint(obj)

		"""

		return self.Database[collection]


	async def delete(self, collection: str, obj_id):
		"""
		Delete object from `collection` by its `obj_id`

		:param collection: Collection to delete from
		:param obj_id: Object identification
		:return: `obj_id` -- Object identification

		Raises:
			KeyError: If `obj_id` not found in `collection`
		"""
		coll = self.Database[collection]
		ret = await coll.find_one_and_delete({'_id': obj_id})
		if ret is None:
			raise KeyError("NOT-FOUND")
		return ret['_id']


class MongoDBUpsertor(UpsertorABC):


	@classmethod
	def generate_id(cls):
		return bson.objectid.ObjectId()


	async def execute(self, custom_data: typing.Optional[dict] = None):
		id_name = self.get_id_name()
		addobj = {}

		if len(self.ModSet) > 0:
			addobj['$set'] = self.ModSet

		if len(self.ModInc) > 0:
			addobj['$inc'] = self.ModInc

		if len(self.ModPush) > 0:
			addobj['$push'] = {k: {'$each': v} for k, v in self.ModPush.items()}

		if len(self.ModUnset) > 0:
			addobj['$unset'] = {k: "" for k in self.ModUnset}

		filtr = {}

		if self.ObjId is not None:
			filtr[id_name] = self.ObjId
		else:
			# We are going to insert a new object without explicit Id
			assert (self.Version == 0) or (self.Version is None)

		if self.Version is not None:
			filtr['_v'] = int(self.Version)

		# First wave (adding stuff)
		if len(addobj) > 0:
			coll = self.Storage.Database[self.Collection]
			try:
				ret = await coll.find_one_and_update(
					filtr,
					update=addobj,
					upsert=True if (self.Version == 0) or (self.Version is None) else False,
					return_document=pymongo.collection.ReturnDocument.AFTER
				)
			except pymongo.errors.DuplicateKeyError as e:
				if hasattr(e, "details"):
					raise DuplicateError("Duplicate key error: {}".format(e), self.ObjId, key_value=e.details.get("keyValue"))
				else:
					raise DuplicateError("Duplicate key error: {}".format(e), self.ObjId)

			if ret is None:
				# Object might have been changed in the meantime
				raise KeyError("NOT-FOUND")

			self.ObjId = ret[id_name]

		# for k, v in self.ModPull.items():
		# 	o = obj.pop(k, None)
		# 	if o is None: o = list()
		# 	for x in v:
		# 		try:
		# 			o.remove(x)
		# 		except ValueError:
		# 			pass
		# 	obj[k] = o

		if self.Storage.WebhookURI is not None:
			webhook_data = {
				"collection": self.Collection,
			}

			if custom_data is not None:
				webhook_data["custom"] = custom_data

			# Add upsetor data; do not include fields that start with "__"
			upsertor_data = {
				"id_field_name": id_name,
				"id": self.ObjId,
				"_v": int(self.Version),
			}
			if len(self.ModSet) > 0:
				upsertor_data["set"] = {k: v for k, v in self.ModSet.items() if not k.startswith("__")}
			if len(self.ModInc) > 0:
				upsertor_data["inc"] = {k: v for k, v in self.ModInc.items() if not k.startswith("__")}
			if len(self.ModPush) > 0:
				upsertor_data["push"] = {k: v for k, v in self.ModPush.items() if not k.startswith("__")}
			if len(self.ModUnset) > 0:
				upsertor_data["unset"] = {k: v for k, v in self.ModUnset.items() if not k.startswith("__")}
			webhook_data["upsertor"] = upsertor_data

			await self._webhook(webhook_data)

		return self.ObjId
