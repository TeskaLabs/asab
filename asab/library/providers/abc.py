

class LibraryProviderABC(object):

	def __init__(self, app, splang_instance, path):
		super().__init__()
		self.App = app
		self.SPLangInstance = splang_instance


	async def initialize(self):
		pass


	async def read(self, path):
		"""
		Reads a declaration on the given path.
		"""
		pass


	async def list(self, path):
		"""
		Lists declarations on the given path.
		"""
		pass


	async def write(self, path, data):
		"""
		Writes the data into the path.
		"""
		pass
