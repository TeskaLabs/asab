from .service import StorageServiceABC
from .upsertor import UpsertorABC
from .exceptions import DuplicateError

class InMemoryUpsertor(UpsertorABC):


	async def execute(self):
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
			if o is None: o = list()
			o.extend(v)
			obj[k] = o

		for k, v in self.ModPull.items():
			o = obj.pop(k, None)
			if o is None: o = list()
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


	def upsertor(self, collection:str, obj_id, version=None):
		return InMemoryUpsertor(self, collection, obj_id, version)


	async def get(self, collection:str, obj_id):
		coll = self.InMemoryCollections[collection]
		return coll[obj_id]


	async def delete(self, collection:str, obj_id):
		coll = self.InMemoryCollections[collection]
		del coll[obj_id]


	def _set(self, collection:str, obj_id, obj):
		try:
			coll = self.InMemoryCollections[collection]
		except KeyError:
			coll = {}
			self.InMemoryCollections[collection] = coll

		nobj = coll.setdefault(obj_id, obj)
		if nobj != obj:
			raise DuplicateError("Already exists", obj_id)

