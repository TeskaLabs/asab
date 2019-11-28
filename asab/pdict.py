import collections
import os
import shelve


class PersistentDict(collections.MutableMapping):

	"""
	The persistent dictionary works as the regular Python dictionary but the content of the dictionary is stored in the file.
	You cat think of a ``PersistentDict`` as a simple `key-value store <https://en.wikipedia.org/wiki/Key-value_database>`_.
	It is not optimized for a frequent access. This class provides common ``dict`` interface.

	*Warning*: You can only store objects in the persistent dictionary that are serializable.
	"""

	def __init__(self, path):
		# Create directory, if needed
		dirname = os.path.dirname(path)
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		self._path = path

	def __getitem__(self, key):
		with shelve.open(self._path) as d:
			return d[key]

	def __setitem__(self, key, value):
		with shelve.open(self._path) as d:
			d[key] = value

	def __delitem__(self, key):
		with shelve.open(self._path) as d:
			del d[key]

	def __iter__(self):
		with shelve.open(self._path) as d:
			for key in d:
				yield key

	def __len__(self):
		with shelve.open(self._path) as d:
			return len(d)

	def __str__(self):
		with shelve.open(self._path) as d:
			return str(dict(d))

	def load(self, *keys):
		"""
		D.load([keys]) -> [values].

		Optimised version of the get() operations that load multiple keys from the persistent store at once.
		It saves IO in exchange for possible race conditions.

		:param keys: A list of keys.
		:return: A list of values in the same order to provided key list.

		.. code:: python

			v1, v2, v3 = pdict.load('k1', 'k2', 'k3')

		"""
		with shelve.open(self._path) as d:
			return (d[key] for key in keys)

	def update(self, other=(), **kwds):
		"""
		D.update([E, ]**F) -> None.

		Update D from mapping/iterable E and F.
		* If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
		* If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
		* In either case, this is followed by: for k, v in F.items(): D[k] = v

		Inspired by a https://github.com/python/cpython/blob/3.8/Lib/_collections_abc.py
		"""

		with shelve.open(self._path) as d:
			if isinstance(other, collections.Mapping):
				for key in other:
					d[key] = other[key]
			elif hasattr(other, "keys"):
				for key in other.keys():
					d[key] = other[key]
			else:
				for key, value in other:
					d[key] = value

			for key, value in kwds.items():
				d[key] = value
