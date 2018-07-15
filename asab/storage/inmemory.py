from .service import StorageServiceABC
from .upsertor import UpsertorABC


class InMemoryUpsertor(UpsertorABC):


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
			self.Storage._set(self.Collection, pk, obj)
		else:
			obj = await self.Storage.get(self.Collection, pk)


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

		return pk


class StorageService(StorageServiceABC):


	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.InMemoryCollections = {}


	def upsertor(self, collection, origObj=None):
		return InMemoryUpsertor(self, collection, origObj)


	async def get(self, collection:str, pk):
		coll = self.InMemoryCollections[collection]
		return coll[pk]


	async def delete(self, collection:str, pk):
		coll = self.InMemoryCollections[collection]
		del coll[pk]


	def _set(self, collection:str, pk, obj):
		try:
			coll = self.InMemoryCollections[collection]
		except KeyError:
			coll = {}
			self.InMemoryCollections[collection] = coll

		coll[pk] = obj
