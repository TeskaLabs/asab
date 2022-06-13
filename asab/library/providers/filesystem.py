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
		library_path_to_replace = "[string_start]{}/".format(os.path.abspath(self.LibraryBaseDir))
		labeled_file_names = ["[string_start]" + i for i in file_names]
		file_names_list = [i.replace(library_path_to_replace, '') for i in labeled_file_names]

		# Results of glob are returned in arbitrary order
		# Sort them to preserver order of parsers
		file_names_list.sort()

		return file_names_list
