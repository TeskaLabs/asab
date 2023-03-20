import typing
from .service import StorageServiceABC
from .upsertor import UpsertorABC
from .exceptions import DuplicateError


class InMemoryUpsertor(UpsertorABC):


	async def execute(self, custom_data: typing.Optional[dict] = None, event_type: typing.Optional[str] = None) -> typing.Union[str, bytes]:
		"""Commit the changes prepared in upsertor.

		:custom_data (dict, optional): Not implemented yet. Defaults to None.
		:event_type (str, optional): Not implemented yet. Defaults to None.

		Raises: :RuntimeError: Raised if the object ID was not found in the previous version.

		Returns:
			:str | bytes: ID of the created or updated document.
		"""

		# TODO: Implement webhook call
		id_name = self.get_id_name()

		# Get the object
		if self.Version == 0:
			obj = {
				id_name: self.ObjId
			}
			self.Storage._set(self.Collection, self.ObjId, obj)

		else:
			obj = await self.Storage.get(self.Collection, self.ObjId)
			if obj is None:
				if self.Version is None:
					obj = {
						id_name: self.ObjId
					}
					self.Storage._set(self.Collection, self.ObjId, obj)
				else:
					raise RuntimeError("Previous version of '{}' not found".format(self.ObjId))


		for k, v in self.ModSet.items():
			obj[k] = v

		for k, v in self.ModUnset.items():
			obj.pop(k, None)

		for k, v in self.ModInc.items():
			o = obj.pop(k, 0)
			obj[k] = o + v

		for k, v in self.ModPush.items():
			o = obj.pop(k, None)
			if o is None:
				o = list()
			o.extend(v)
			obj[k] = o

		for k, v in self.ModPull.items():
			o = obj.pop(k, None)
			if o is None:
				o = list()
			for x in v:
				try:
					o.remove(x)
				except ValueError:
					pass
			obj[k] = o

		return self.ObjId


class StorageService(StorageServiceABC):


	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.InMemoryCollections = {}


	def upsertor(self, collection: str, obj_id=None, version=0) -> InMemoryUpsertor:
		"""Obtain an in-memory upsertor for given collection and possibly for the specified object.

		:collection (str): The name of the collection.
		:obj_id (_type_, optional): The ID of the document to retrieve. Defaults to None.
		:version (int, optional): The version of the collection. Defaults to 0.

		Returns:
			:InMemoryUpsertor: Upsertor for given collection.

		"""
		return InMemoryUpsertor(self, collection, obj_id, version)


	async def get(self, collection: str, obj_id: typing.Union[str, bytes], decrypt=None) -> dict:
		"""Retrieve a document from an in-memory collection by its ID.

		:collection (str): The name of the collection to retrieve the document from.
		:obj_id (str | bytes): The ID of the document to retrieve.
		:decrypt (_type_, optional): A list of field names to decrypt. Defaults to None.

		Returns:
			:dict: A dictionary representing the retrieved document.bIf `decrypt` is not None, the specified fields in the document are decrypted using AES decryption algorithm.

		"""
		coll = self.InMemoryCollections[collection]
		data = coll[obj_id]
		if decrypt is not None:
			for field in decrypt:
				if field in data:
					data[field] = self.aes_decrypt(data[field])
		return data


	async def get_by(self, collection: str, key: str, value, decrypt=None) -> dict:
		"""
		Retrieve a document from an in-memory collection by key and value. Not implemented yet.

		Raises:
			:NotImplementedError: Not implemented on InMemoryStorage
		"""
		raise NotImplementedError()


	async def delete(self, collection: str, obj_id):
		"""
		Delete a document from an in-memory collection.

		:param collection: Collection to delete from
		:param obj_id: Object identification

		Raises:
			:KeyError: If `obj_id` not found in `collection`
		"""
		coll = self.InMemoryCollections[collection]
		del coll[obj_id]


	def _set(self, collection: str, obj_id, obj):
		try:
			coll = self.InMemoryCollections[collection]
		except KeyError:
			coll = {}
			self.InMemoryCollections[collection] = coll

		nobj = coll.setdefault(obj_id, obj)
		if nobj != obj:
			raise DuplicateError("Already exists", obj_id)
