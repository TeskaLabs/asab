import os
import time
import logging
import pickle
import collections
import contextlib


@contextlib.contextmanager
def persistent_dict_file(fname, save=False):
	fname_lock = fname+'.lock'
	fd = 0
	try:

		# Lock the file
		start_time = time.time()
		while True:
			try:
				fd = os.open(fname_lock, os.O_CREAT | os.O_EXCL | os.O_RDWR)
				break;
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise 
				if (time.time() - start_time) >= 60:
					raise FileLockException("Timeout occured.")
				time.sleep(1)

		# Load the persistent data
		try:
			with open(fname, 'rb') as f:
				dictionary = pickle.load(f)
		except FileNotFoundError:
			dictionary = {}

		if not save:
			os.close(fd)
			os.unlink(fname_lock)
			fd = 0

		yield dictionary

		if save:
			with open(fname, 'wb') as f:
				pickle.dump(dictionary, f)

	finally:

		# Unlock the file
		if fd != 0:
			os.close(fd)
		if os.path.exists(fname_lock):
			os.unlink(fname_lock)


class PersistentDict(collections.MutableMapping):

	'''
 Note: Clever way of initializing of the persistent dict is a use of setdefault:

PersistentState = asab.PersistentDict("some.file")
PersistentState.setdefault('foo', 0)
PersistentState.setdefault('bar', 2)

	'''


	def __init__(self, path):
		# Create directory, if needed
		dirname = os.path.dirname(path)
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		self._path = path

	def __getitem__(self, key):
		with persistent_dict_file(self._path) as d:
			return d[key]

	def __setitem__(self, key, value):
		with persistent_dict_file(self._path, save=True) as d:
			d[key] = value

	def __delitem__(self, key):
		with persistent_dict_file(self._path, save=True) as d:
			del d[key]

	def __iter__(self):
		with persistent_dict_file(self._path) as d:
			return iter(d)

	def __len__(self):
		with persistent_dict_file(self._path) as d:
			return len(d)

	def __str__(self):
		with persistent_dict_file(self._path) as d:
			return str(d)

	def load(self, *keys):
		'''
		Optimised version of the get() operations that load multiple keys from the persistent store at once.
		It saves IO in exchange for possible race conditions.
		'''
		with persistent_dict_file(self._path) as d:
			return (d[key] for key in keys)

	def update(*args, **kwds):
		'''D.update([E, ]**F) -> None.  Update D from mapping/iterable E and F.
			If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
			If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
			In either case, this is followed by: for k, v in F.items(): D[k] = v

			Inspired by a https://github.com/python/cpython/blob/3.6/Lib/_collections_abc.py
		'''
		self, *args = args
		if len(args) > 1:
			raise TypeError('update expected at most 1 arguments, got %d' % len(args))

		with persistent_dict_file(self._path, save=True) as d:
			if args:
				other = args[0]
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
