'''
apk add pymongo
apk add motor
'''

import motor.motor_asyncio
import pymongo

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

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Client = motor.motor_asyncio.AsyncIOMotorClient(asab.Config.get('asab:storage', 'mongodb_uri'))
		self.Database = self.Client[asab.Config.get('asab:storage', 'mongodb_database')]


	def upsertor(self, collection: str, obj_id=None, version=0):
		return MongoDBUpsertor(self, collection, obj_id, version)


	async def get(self, collection: str, obj_id) -> dict:
		coll = self.Database[collection]
		ret = await coll.find_one({'_id': obj_id})
		if ret is None:
			raise KeyError("NOT-FOUND")
		return ret


	async def get_by(self, collection: str, key: str, value) -> dict:
		"""
		Get object from collection by its key/value

		:param collection: Collection to get from
		:param key: Key to filter on
		:param value: Value to filter on
		:return: The object retrieved from a storage

		Raises:
			KeyError: If object{key: value} not found in `collection`
		"""
		coll = self.Database[collection]
		ret = await coll.find_one({key: value})
		if ret is None:
			raise KeyError("NOT-FOUND")
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


	async def execute(self):
		id_name = self.get_id_name()
		addobj = {}

		if len(self.ModSet) > 0:
			addobj['$set'] = self.ModSet

		if len(self.ModInc) > 0:
			addobj['$inc'] = self.ModInc

		if len(self.ModPush) > 0:
			addobj['$push'] = {k: {'$each': v} for k, v in self.ModPush.items()}

		filter = {id_name: self.ObjId}
		if self.Version is not None:
			filter['_v'] = int(self.Version)

		# First wave (adding stuff)
		if len(addobj) > 0:
			coll = self.Storage.Database[self.Collection]

			try:
				ret = await coll.find_one_and_update(
					filter,
					update=addobj,
					upsert=True if (self.Version == 0) or (self.Version is None) else False,
					return_document=pymongo.collection.ReturnDocument.AFTER
				)
			except pymongo.errors.DuplicateKeyError:
				assert(self.Version == 0)
				raise DuplicateError("Already exists", self.ObjId)

			self.ObjId = ret[id_name]

		# for k, v in self.ModUnset.items():
		# 	obj.pop(k, None)

		# for k, v in self.ModPull.items():
		# 	o = obj.pop(k, None)
		# 	if o is None: o = list()
		# 	for x in v:
		# 		try:
		# 			o.remove(x)
		# 		except ValueError:
		# 			pass
		# 	obj[k] = o

		return self.ObjId
