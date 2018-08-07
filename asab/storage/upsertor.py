import abc
import uuid
import hashlib
import datetime

class UpsertorABC(abc.ABC):

	def __init__(self, storage, collection, obj_id, version=None):
		'''
		'''

		self.Storage = storage
		self.Collection = collection
		self.ObjId = obj_id

		self.Version = version

		now = datetime.datetime.utcnow()
		self.ModSet = {
			'_m': now, # Set the modification timestamp
		}
		if version == 0:
			self.ModSet['_c'] = now # Set the creation timestamp

		self.ModUnset = {}

		self.ModInc = {
			'_v' : 1, # Increment '_v' at every change
		}

		self.ModPush = {}
		self.ModPull = {}


	def get_id_name(self):
		return "_id"


	def generate_id(self):
		m = hashlib.sha384()
		m.update(uuid.uuid4().bytes)
		m.update(uuid.uuid4().bytes)
		m.update(uuid.uuid4().bytes)
		return m.hexdigest()


	def set(self, objField, value):
		'''
		Scalar set
		'''
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
	async def execute(self):
		pass
