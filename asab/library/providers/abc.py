import typing


class LibraryProviderABC(object):


	def __init__(self, library, layer):
		super().__init__()
		self.App = library.App
		self.Library = library
		self.Layer = layer
		self.IsReady = False


	async def finalize(self, app):
		pass


	async def read(self, path: str, tenant: str) -> typing.IO:
		"""
		Reads a library item on the given path.

		:param path: The path to the item to read
		:return: I/O stream (read) with the content of the library item.
		"""
		raise NotImplementedError("{}.read()".format(self.__class__.__name__))


	async def list(self, path: str, tenant: str) -> list:
		"""
		It lists all items in the library at the given path.

		:param path: The path to the directory in the library to list
		:return: A list (or iterable) of `LibraryItem`s.
		"""
		raise NotImplementedError("{}.list()".format(self.__class__.__name__))


	async def _set_ready(self, ready=True):
		self.IsReady = ready
		await self.Library._set_ready(self)

	async def subscribe(self, path: str):
		"""
		It takes a path and subscribes to changes in this directory.
		When change occurs, it creates a PubSub signal.
		Use absolute path, startng with "/".
		Keep in mind every provider requires specific implementation. These might vary in lag between change if the librarby and its propagation.

		Mind following when implementing this method:
		- user can subscribe only on existing directory. -> Check whether subscribed path is a directory, specifically in the provider
		- subscribing to nonexisting directory or file should lead to silent error

		"""
		raise NotImplementedError("{}.subscribe()".format(self.__class__.__name__))
