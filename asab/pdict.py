import collections
import os
import shelve


class PersistentDict(dict):
	"""
	The persistent dictionary works as the regular Python dictionary but the content of the dictionary is stored in the file.
	You cat think of a `PersistentDict` as a simple [key-value store](https://en.wikipedia.org/wiki/Key-value_database).
	It is not optimized for a frequent access. This class provides common `dict` interface.

	Example:
		```python
		class MyApplication(asab.Application):
			async def main(self):
				pdict = asab.PersistentDict('./pdict.bin')
				pdict.load()
				counter = pdict['counter'] = pdict.setdefault('counter', 0) + 1
				print("Executed for {} times".format(counter))
				pdict.store()
				self.stop()
		```

	!!! warning
		You must explicitly `load()` and `store()` content of the dictionary!

	!!! warning
		You can only store objects in the persistent dictionary that are serializable.
	"""

	def __init__(self, path: str):
		"""Initialize persistent dictionary.

		Args:
			path (str): Path for the dictionary file.
		"""
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
		Store content of persistent dictionary to a file.
		"""

		with shelve.open(self._path) as d:
			for key, value in self.items():
				d[key] = value

	def update(self, other={}, **kwds) -> None:
		"""
		Update persistent dictionary from mapping or iterable.

		Examples:
			```python
				>>> pdict.update({'foo': 'bar', 'moo': 'buzz'})
				>>> pdict.update(foo='bar', moo='buzz')
				>>> pdict.update([('foo','bar'),('moo','buzz')])
			```

		Args:
			other: Dictionary or iterable of 2-tuples of the form (key, value) to be updated.
		"""

		if isinstance(other, collections.abc.Mapping):
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
