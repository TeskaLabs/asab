

class LibraryProviderABC(object):

	def __init__(self, app, path):
		super().__init__()
		self.App = app

	async def read(self, path):
		"""
		Reads a declaration on the given path.
		"""
		pass


	async def list(self, path, tenant=None, recursive=False):
		"""
		Lists declarations on the given path.
		"""
		pass
