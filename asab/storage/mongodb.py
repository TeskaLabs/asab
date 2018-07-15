import pprint

import pymongo
import bson.binary
import motor.motor_asyncio

import asab

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
		self.Client = motor.motor_asyncio.AsyncIOMotorClient(asab.Config.get('seacatca:mongodb', 'uri'))
		self.Database = self.Client[asab.Config.get('seacatca:mongodb', 'database')]


	def upsertor(self, collection, origObj=None):
		return MongoDBUpsertor(self, collection, origObj)


	async def get(self, collection:str, pk):
		coll = self.Database[collection]
		ret = await coll.find_one({'_id': pk})
		if ret is None:
			raise KeyError("NOT-FOUND")
		return ret


	async def delete(self, collection:str, pk):
		coll = self.Database[collection]
		ret = await coll.find_one_and_delete({'_id': pk})
		if ret is None:
			raise KeyError("NOT-FOUND")
		return ret['_id']


class MongoDBUpsertor(UpsertorABC):


	async def execute(self):

		# Primary key
		pk_name = self.get_pk_name()
		if self.IsNew:
			pk = self.ModSet.pop(pk_name, None)
			if pk is None:
				pk = self.generate_pk()
		else:
			pk = self.OrigObj.get(pk_name)

		# Get the object
		if self.IsNew:
			obj = {
				pk_name: pk
			}
		else:
			obj = self.Storage.get(self.Collection, pk)


		addobj = {}

		if len(self.ModSet) > 0:
			addobj['$set'] = self.ModSet

		if len(self.ModInc) > 0:
			addobj['$inc'] = self.ModInc

		if len(self.ModPush) > 0:
			addobj['$push'] = { k : {'$each': v} for k, v in self.ModPush.items()}


		filter = {'_id' : pk}
		if not self.IsNew:
			filter['_v'] = self.OrigObj.get('_v')


		# First wave (adding stuff)
		if len(addobj) > 0:
			coll = self.Storage.Database[self.Collection]
			ret = await coll.find_one_and_update(
				filter,
				update = addobj,
				upsert = self.IsNew,
				return_document = pymongo.collection.ReturnDocument.AFTER
			)
			pk = ret['_id']


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

		return pk
