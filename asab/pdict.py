import collections
import os
import shelve


class PersistentDict(dict):

	"""
	The persistent dictionary works as the regular Python dictionary but the content of the dictionary is stored in the file.
	You cat think of a ``PersistentDict`` as a simple `key-value store <https://en.wikipedia.org/wiki/Key-value_database>`_.
	It is not optimized for a frequent access. This class provides common ``dict`` interface.

	*Warning*: You must explicitly `load()` and `store()` content of the dictionary
	*Warning*: You can only store objects in the persistent dictionary that are serializable.
	"""

	def __init__(self, path):
		super().__init__()
		# Create directory, if needed
		dirname = os.path.dirname(path)
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		self._path = path

	def __delitem__(self, key):
		super().__delitem__(key)
		with shelve.open(self._path) as d:
			del d[key]

	def load(self) -> None:
		"""
		Load content of file as dictionary.
		"""
		with shelve.open(self._path) as d:
			for key, value in d.items():
				self[key] = value

	def store(self) -> None:
		"""
		Explicitly store content of persistent dictionary to file
		"""

		with shelve.open(self._path) as d:
			for key, value in self.items():
				d[key] = value

	def update(self, other=(), **kwds) -> None:
		"""
		Update D from mapping/iterable E and F.
		* If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
		* If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
		* In either case, this is followed by: for k, v in F.items(): D[k] = v

		Inspired by a https://github.com/python/cpython/blob/3.8/Lib/_collections_abc.py
		"""

		if isinstance(other, collections.Mapping):
			for key in other:
				self[key] = other[key]
		elif hasattr(other, "keys"):
			for key in other.keys():
				self[key] = other[key]
		else:
			for key, value in other:
				self[key] = value

		for key, value in kwds.items():
			self[key] = value
