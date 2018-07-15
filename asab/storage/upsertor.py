import abc
import uuid
import hashlib

class UpsertorABC(abc.ABC):

	def __init__(self, storage, collection, origObj=None):

		self.Storage = storage
		self.Collection = collection
		self.OrigObj = origObj
		self.IsNew 	= origObj is None or origObj == {}

		self.ModSet = {}
		self.ModUnset = {}

		self.ModInc = { '_v' : 1 } # Increment '_v' at every change

		self.ModPush = {}
		self.ModPull = {}


	def get_pk_name(self):
		return "_id"


	def generate_pk(self):
		m = hashlib.sha384()
		m.update(uuid.uuid4().bytes)
		m.update(uuid.uuid4().bytes)
		m.update(uuid.uuid4().bytes)
		return m.hexdigest()


	def _get_value(self, dotConvField):
		v = self.OrigObj
		for k in dotConvField.split('.'):
			if not isinstance(v, dict): raise RuntimeError("Dictionary is expected.")
			v = v.get(k)
			if v is None: break;
		return v


	def set(self, objField, value):
		'''
		Scalar set
		'''
		origVal = None if self.IsNew else self._get_value(objField)

		if origVal == value:
			return False
		if origVal is None and value is '' :
			return False

		if value is None or value == '':
			self.unset(objField)
		else:
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
