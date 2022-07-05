

class LibraryProviderABC(object):

	# List of extensions that are allowed to be present in the library
	FileExtentions = {'.yaml', '.json'}

	def __init__(self, app, path):
		super().__init__()
		self.App = app


	async def finalize(self, app):
		pass


	async def read(self, path: str) -> bytes:
		"""
		Reads a library item on the given path.
		
		:param path: The path to the file to read
		:return: The item a bytes.
		"""

		pass


	async def list(self, path: str, tenant:str =None, recursive:bool =False) -> list:
		"""
		It lists all items in the library .
		
		:param path: The path to the directory in the library to list
		:param recursive: If True, recursively list all files in the directory, defaults to True (optional)
		:return: A sorted list of file names
		"""
		pass
