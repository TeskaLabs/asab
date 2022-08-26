import io
import os
import stat
import glob
import typing
import functools
import logging

from .abc import LibraryProviderABC
from ..item import LibraryItem

#

L = logging.getLogger(__name__)

#


class FileSystemLibraryProvider(LibraryProviderABC):


	def __init__(self, library, path, *, set_ready=True):
		'''
		`set_ready` can be used to disable/defer `self._set_ready` call.
		'''

		super().__init__(library)
		self.BasePath = os.path.abspath(path)
		while self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]

		L.info("is connected.", struct_data={'path': path})
		# Filesystem is always ready (or you have a serious problem)
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())


	async def read(self, path: str) -> typing.IO:

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		try:
			return io.FileIO(node_path, 'rb')

		except FileNotFoundError:
			return None

		except IsADirectoryError:
			return None


	async def list(self, path: str) -> list:

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		iglobpath = os.path.join(node_path, "*")

		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Not '{}' found".format(path))

		items = []
		for fname in glob.iglob(iglobpath):

			fstat = os.stat(fname)

			assert fname.startswith(node_path)
			fname = fname[len(node_path) + 1:]

			if stat.S_ISREG(fstat.st_mode):
				ftype = "item"
			elif stat.S_ISDIR(fstat.st_mode):
				ftype = "dir"
			else:
				ftype = "?"

			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), fname.split(os.path.sep), False)
			if startswithdot:
				continue

			items.append(LibraryItem(
				name=(path + fname) if path == '/' else (path + '/' + fname),
				type=ftype,
				providers=[self],
			))

		return items
