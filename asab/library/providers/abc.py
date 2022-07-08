

class LibraryProviderABC(object):


	def __init__(self, library):
		super().__init__()
		self.App = library.App
		self.Library = library
		self.IsReady = False


	async def finalize(self, app):
		pass


	async def read(self, path: str) -> bytes:
		"""
		Reads a library item on the given path.

		:param path: The path to the file to read
		:return: The item a bytes.
		"""
		raise NotImplementedError("{}.read()".format(self.__class__.__name__))


	async def list(self, path: str) -> list:
		"""
		It lists all items in the library at the given path.

		:param path: The path to the directory in the library to list
		:return: A list (or iterable) of `LibraryItem`s.
		"""
		raise NotImplementedError("{}.list()".format(self.__class__.__name__))


	async def _set_ready(self):
		self.IsReady = True
		await self.Library._set_ready(self)
