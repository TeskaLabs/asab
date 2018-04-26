import time
import hashlib
import asyncio
import collections

class Session(collections.MutableMapping):

	"""Session dict-like object."""

	def __init__(self, storage, id, new, max_age=None):
		self._id = id
		self._changed = False
		self._mapping = {}
		self._new = new
		self.MaxAge = max_age
		self.Storage = storage

		if new or created is None:
			self._created = int(time.time())
		else:
			self._created = created


	def __hash__(self):
		return hash((self.__class__, self._id))


	def __repr__(self):
		return '<{} [{}, new:{}, changed:{}, created:{} expired:{}] {!r}>'.format(
			self.__class__.__name__,
			hashlib.sha224(self._id.encode('utf-8')).hexdigest() if self._id is not None else "-",
			self._new, self._changed ,self._created, self.is_expired(), self._mapping
		)


	def is_expired(self):
		expiration = self._created + self.MaxAge
		if time.time() >= expiration: return True
		return False


	def reset(self):
		self._new = False
		self._change = False


	@property
	def Id(self):
		return self._id

	def set_id(self, id):
		if self._id is not None or self._new == False:
			raise RuntimeError("Session id is already set!")
		self._id = id


	@property
	def Created(self):
		return self._created


	def is_new(self):
		return self._new

	def mark_changed(self):
		self._changed = True



	def __len__(self):
		return len(self._mapping)

	def __iter__(self):
		return iter(self._mapping)

	def __contains__(self, key):
		return key in self._mapping

	def __getitem__(self, key):
		return self._mapping[key]

	def __setitem__(self, key, value):
		self._mapping[key] = value
		self._changed = True

	def __delitem__(self, key):
		del self._mapping[key]
		self._changed = True
