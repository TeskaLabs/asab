

class LibraryProviderABC(object):

	# List of extensions that are allowed to be present in the library
	FileExtentions = {'.yaml', '.json'}

	def __init__(self, app, path):
		super().__init__()
		self.App = app


	async def finalize(self, app):
		pass


	async def read(self, path):
		"""
		Reads a declaration on the given path.

		Returns 'bytes' or 'None' if the path doesn't exists or point to a readable library object.
		"""
		pass


	async def list(self, path, tenant=None, recursive=False):
		"""
		Lists declarations on the given path.
		"""
		pass
