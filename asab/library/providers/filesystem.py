import functools
import glob
import os

from .abc import LibraryProviderABC


class FileSystemLibraryProvider(LibraryProviderABC):


	def __init__(self, app, path):
		super().__init__(app, path)
		self.LibraryBaseDir = path


	async def read(self, path):
		basepath = os.path.join(self.LibraryBaseDir, path)

		try:
			with open(basepath, 'rb') as f:
				return f.read()

		except FileNotFoundError:
			return None

		except IsADirectoryError:
			return None


	async def list(self, path, recursive=True):

		basepath = os.path.join(self.LibraryBaseDir, path)

		if recursive:
			iglobpath = os.path.join(basepath, "**")
		else:
			iglobpath = basepath

		exists = os.access(basepath, os.R_OK) and os.path.isdir(basepath)
		if not exists:
			return None

		file_names = []
		for fname in glob.iglob(iglobpath, recursive=recursive):
			fnamep, ext = os.path.splitext(fname)

			if ext not in self.FileExtentions:
				continue

			if not os.path.isfile(fname):
				continue

			assert(fname.startswith(basepath))
			fname = fname[len(basepath):]

			fnamecomp = fname.split(os.path.sep)  # Split by "/"

			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), fnamecomp, False)
			if startswithdot:
				continue

			file_names.append(fname)

		# Results of glob are returned in arbitrary order
		# Sort them to preserver order of parsers
		file_names.sort()

		return file_names
