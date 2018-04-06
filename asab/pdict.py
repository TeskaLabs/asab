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
