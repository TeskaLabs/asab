import datetime
import typing
import functools

import motor.motor_asyncio
import pymongo

import bson
import logging

import asab
from .exceptions import DuplicateError, DryRunAbort
from .service import StorageServiceABC
from .upsertor import UpsertorABC
from .dry_run import DRY_RUN

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:storage': {
			'mongodb_uri': '',
			'mongodb_database': '',
		}
	}
)


def transactional(method_to_decorate):
	@functools.wraps(method_to_decorate)
	async def wrapper(*args, **kwargs):
		inst_self = args[0]
		decorated_method_args = args[1:]

		if isinstance(inst_self, asab.storage.mongodb.MongoDBUpsertor):
			client = inst_self.Storage.Client
			obj_id = inst_self.ObjId
		else:
			client = inst_self.Client
			_, obj_id = decorated_method_args

		async with await client.start_session() as session:
			try:
				session.start_transaction(
					read_concern=pymongo.read_concern.ReadConcern("local"),
					write_concern=pymongo.write_concern.WriteConcern("majority")
				)
				result = await method_to_decorate(inst_self, session, *decorated_method_args, **kwargs)

				dry_run = DRY_RUN.get("dry_run")
				if dry_run:
					if session.in_transaction:
						await session.abort_transaction()


					raise DryRunAbort(obj_id=obj_id)

				if session.in_transaction:
					await session.commit_transaction()
				return result

			except DryRunAbort:
				return obj_id
			except DuplicateError:
				if session.in_transaction:
					await session.abort_transaction()
				raise
			except Exception as e:
				L.exception("Unknown exception encountered while executing MongoDB transaction: {}".format(e))
				if session.in_transaction:
					await session.abort_transaction()
				raise
	return wrapper


class StorageService(StorageServiceABC):
	'''
	StorageService for MongoDB. Depends on `pymongo` and `motor`.
	'''


	def __init__(self, app, service_name, config_section_name='asab:storage'):
		super().__init__(app, service_name)

		# Check the old section and then the new section for uri
		uri = asab.Config.get(config_section_name, 'mongodb_uri', fallback='')

		if len(uri) == 0:
			uri = asab.Config.get("mongo", 'uri', fallback='')

		if len(uri) == 0:
			raise RuntimeError("No MongoDB URI has been provided.")

		self.Client = motor.motor_asyncio.AsyncIOMotorClient(uri)

		# Check the old section and then the new section for database name
		db_name = asab.Config.get(config_section_name, 'mongodb_database', fallback='')
		if len(db_name) == 0:
			db_name = asab.Config.get('mongo', 'database', fallback='')

		self.Database = self.Client.get_database(
			db_name,
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
			await self._decrypt(ret, fields=decrypt, collection=collection)

		return ret


	async def get_by(self, collection: str, key: str, value, decrypt=None) -> dict:
		coll = self.Database[collection]
		ret = await coll.find_one({key: value})

		if ret is None:
			raise KeyError("NOT-FOUND")

		if decrypt is not None:
			await self._decrypt(ret, fields=decrypt, collection=collection)

		return ret


	async def collection(self, collection: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
		"""
		Get collection. Useful for custom operations.
		"""

		return self.Database[collection]

	@transactional
	async def delete(self, session, collection: str, obj_id):
		coll = self.Database[collection]
		ret = await coll.find_one_and_delete({'_id': obj_id}, session=session)

		if ret is None:
			raise KeyError("NOT-FOUND")

		return ret['_id']


	async def list(self, collection_name: str, _from: int = 0, size: int = 0, _filter=None, sorts=None):
		"""
		Lists all the elements in the collection starting from _from and ending with size (unless the size is 0).
		"""
		collection = self.Database[collection_name]

		# Build filter
		if _filter is None:
			query = {}

		else:
			query = {"_id": {"$regex": f"^{_filter}"}}

		items_cursor = collection.find(query)

		# Apply sorting if needed
		if sorts:
			sort_list = [(field, -1 if descending else 1) for field, descending in sorts]
			items_cursor = items_cursor.sort(sort_list)

		# Apply skip and limit
		if _from:
			items_cursor = items_cursor.skip(_from)

		if size:
			items_cursor = items_cursor.limit(size)

		async for item in items_cursor:
			yield item


	async def rename(self, previous_collection_name, new_collection_name):
		if previous_collection_name == new_collection_name:
			return  # No action needed

		existing_collections = await self.Database.list_collection_names()

		if previous_collection_name not in existing_collections:
			raise KeyError(f"Collection '{previous_collection_name}' does not exist.")

		if new_collection_name in existing_collections:
			raise DuplicateError(f"Collection '{new_collection_name}' already exists.")

		return await self.Database[previous_collection_name].rename(new_collection_name)


	async def count(self, collection_name, _filter=None) -> int:
		"""
		Counts all the elements in the collection.
		"""
		coll = self.Database[collection_name]
		count = await coll.count()
		return count


	async def collections(self, search_string=None):
		return await self.Database.list_collection_names()


	async def update_by_bulk(self, collection_name: str, documents: list) -> dict:
		"""
		Writes all the documents defined by _id and _source to the MongoDB as bulk.
		"""
		bulk = []
		coll = self.Database[collection_name]

		for document in documents:
			doc_id = document.get("_id")
			source = document.get("_source")

			if not doc_id or not source:
				continue  # Skip invalid documents

			bulk.append(
				pymongo.UpdateOne(
					{"_id": doc_id},
					{
						"$set": source,
					},
					upsert=True
				)
			)

		return coll.bulk_write(bulk)


	async def _decrypt(self, db_obj: dict, fields: typing.Iterable, collection: str):
		"""
		Decrypt object fields in-place
		"""
		re_encrypt_fields = {}
		for field in fields:
			if field in db_obj:
				try:
					db_obj[field] = self.aes_decrypt(db_obj[field])
				except ValueError:
					db_obj[field] = self.aes_decrypt(db_obj[field], _obsolete_padding=True)
					re_encrypt_fields[field] = db_obj[field]

		# Update fields encrypted with flawed padding in previous versions (before #587)
		if re_encrypt_fields:
			upsertor = self.upsertor(collection, db_obj["_id"], db_obj["_v"])
			for k, v in re_encrypt_fields.items():
				upsertor.set(k, v, encrypt=True)
			L.debug("Object encryption updated.", struct_data={
				"coll": collection, "_id": db_obj["_id"], "fields": list(re_encrypt_fields)})
			await upsertor.execute()


class MongoDBUpsertor(UpsertorABC):


	@classmethod
	def generate_id(cls):
		return bson.objectid.ObjectId()

	@transactional
	async def execute(self, session, custom_data: typing.Optional[dict] = None, event_type: typing.Optional[str] = None):
		id_name = self.get_id_name()
		addobj = {}

		if len(self.ModSet) > 0:
			addobj['$set'] = self.ModSet

		if len(self.ModInc) > 0:
			addobj['$inc'] = self.ModInc

		if len(self.ModPull) > 0:
			addobj['$pull'] = {k: {'$in': v} for k, v in self.ModPull.items()}

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

		if len(addobj) > 0:
			coll = self.Storage.Database[self.Collection]
			try:
				ret = await coll.find_one_and_update(
					filtr,
					update=addobj,
					upsert=True if (self.Version == 0) or (self.Version is None) else False,
					return_document=pymongo.collection.ReturnDocument.AFTER,
					session=session,
				)
			except pymongo.errors.DuplicateKeyError as e:
				if hasattr(e, "details"):
					raise DuplicateError("Duplicate key error: {}".format(e), self.ObjId, key_value=e.details.get("keyValue"))
				else:
					raise DuplicateError("Duplicate key error: {}".format(e), self.ObjId)

			if ret is None:
				# Object might have been changed in the meantime
				raise KeyError("NOT-FOUND")

			if ret.get('_v') == 1 and '_c' not in ret:
				# If the object is new (version is 1), set the creation datetime
				await coll.update_one(
					{id_name: ret[id_name]},
					{'$set': {'_c': ret['_m']}},
					session=session,
				)

			self.ObjId = ret[id_name]

		if self.Storage.WebhookURIs is not None:
			webhook_data = {
				"collection": self.Collection,
			}

			if custom_data is not None:
				webhook_data["custom"] = custom_data

			if event_type is not None:
				webhook_data["event_type"] = event_type

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

			await self.webhook(webhook_data)

		return self.ObjId
