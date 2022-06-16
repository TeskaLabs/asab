import glob
import os

from .abc import LibraryProviderABC


class FileSystemLibraryProvider(LibraryProviderABC):


	def __init__(self, app, path):
		super().__init__(app, path)

		self.LibraryBaseDir = path


	async def read(self, path):
		file_path = os.path.join(self.LibraryBaseDir, path)

		try:
			with open(file_path, 'rb') as f:
				return f.read()

		except FileNotFoundError:
			return None


	async def list(self, path, recursive=True):

		if recursive:
			path = os.path.join(path, "**")

		file_names = list(
			glob.iglob(
				os.path.join(self.LibraryBaseDir, path),
				recursive=recursive
			)
		)

		# Remove library path from the beginning of file names
		library_path_to_replace = "{}/".format(os.path.abspath(self.LibraryBaseDir))
		for name in file_names:
			assert name.startswith(library_path_to_replace)
		file_names_list = [name[len(library_path_to_replace):] for name in file_names]

		# Results of glob are returned in arbitrary order
		# Sort them to preserver order of parsers
		file_names_list.sort()

		return file_names_list
