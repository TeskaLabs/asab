import re
import logging
import configparser

from ..abc import Service
from ..config import Config

#

L = logging.getLogger(__name__)

#


class LibraryService(Service):

	def __init__(self, app, service_name, paths=None):
		super().__init__(app, service_name)
		self.Libraries = dict()

		if paths is None:
			try:
				paths = Config.get("library", "providers")
			except configparser.NoOptionError:
				L.critical("'providers' option is not present in configuration section 'library'.")
				raise SystemExit("Exit due to a critical configuration error.")

		if isinstance(paths, str):
			paths = re.split(r"\s+", paths)

		for path in paths:
			self._create_library(path)


	async def finalize(self, app):
		while len(self.Libraries) > 0:
			key = next(iter(self.Libraries))
			lib = self.Libraries.pop(key)
			await lib.finalize()


	def _create_library(self, path):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeeper://'):
			from .providers.zookeeper import ZooKeeperLibraryProvider
			library_provider = ZooKeeperLibraryProvider(self.App, path)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			from .providers.filesystem import FileSystemLibraryProvider
			library_provider = FileSystemLibraryProvider(self.App, path)

		else:
			L.error("Incorrect/unknow provider for '{}'".format(path))
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries[path] = library_provider


	# TODO: Read disabled from the first library and apply that on the results of `read` and `list`.


	async def read(self, path, tenant=None):
		for library in self.Libraries.values():
			item = await library.read(path)
			if item is None:
				continue

			# TODO: Filter the `path` using disabled.

			return item

		return None


	async def list(self, path, tenant=None, recursive=False):
		""" 
		Tenant is an optional parameter to list method for "disable" evaluation.
			and default recursive is False.

		When tenant=None
			The method returns list of yaml files that are enabled (not disabled).
		
		When tenant='xxxxx'
			The method returns list of yaml files that are enabled (not disabled) for tenant 'xxxxx'.

		When recursive=True
			returns a list of yaml files located in zero or more directories and
			subdirectories.
		
		When recursive=False
			returns a list of yaml files located in /library.
		"""
		for library in self.Libraries.values():
			listres = await library.list(path, recursive)
			if listres is None:
				continue

			# TODO: Filter the `listres` using disabled.
			return listres

		return None
