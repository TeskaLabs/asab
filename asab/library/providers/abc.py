

class LibraryProviderABC(object):

	def __init__(self, app, path):
		super().__init__()
		self.App = app


	async def initialize(self, app):
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
