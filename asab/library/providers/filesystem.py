import glob
import os

from .abc import LibraryProviderABC


class FileSystemLibraryProvider(LibraryProviderABC):


	def __init__(self, app, splang_instance, path):
		super().__init__(app, splang_instance, path)

		self.LibraryBaseDir = path


	async def initialize(self):
		pass


	async def read(self, path):
		file_path = os.path.join(self.LibraryBaseDir, path)

		if not os.path.isfile(file_path):
			return None

		with open(file_path, 'r') as f:
			return f.read()


	async def list(self, path):
		recursive = path.endswith("*")

		if recursive:
			path = os.path.join(path[:-2], "**")

		file_names = glob.iglob(
			os.path.join(self.LibraryBaseDir, path, "*.yaml"),
			recursive=recursive
		)

		files_names_list = []

		# Remove library path from the beginning of file names
		library_path_to_replace = "{}/".format(os.path.abspath(self.LibraryBaseDir))

		for file_name in file_names:
			files_names_list.append(
				file_name.replace(library_path_to_replace, '')
			)

		# Results of glob are returned in arbitrary order
		# Sort them to preserver order of parsers
		files_names_list.sort()

		return files_names_list


	async def write(self, path, data):

		with open(path, 'w') as f:
			f.write(data)
