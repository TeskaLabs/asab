import re
import logging

from ..abc import Service
from ..config import Config

from .providers.filesystem import FileSystemLibraryProvider
from .providers.zookeeper import ZooKeeperLibraryProvider

#

L = logging.getLogger(__name__)

#


class LibraryService(Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		try:
			paths = Config.get("library", 'providers')
		except configparser.NoOptionError:
			L.critical("'providers' option is not present in configuration section 'library'.")
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries = dict()
		for path in re.split(r"\s+", paths):
			self._create_library(path)


	def _create_library(self, path):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeeper://'):
			library_provider = ZooKeeperLibraryProvider(self.App, path)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			library_provider = FileSystemLibraryProvider(self.App, path)

		else:
			L.error("Incorrect providers passed.")
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries[path] = library_provider


	async def read(self, path):
		for library in self.Libraries.values():
			item = await library.read(path)
			if item is not None:
				return item

	async def list(self, path, tenant=None, recursive=False):
		""" Tenant is an optional parameter to list method for "disable" evaluation.
			and default recursive is False.

			When tenant=None
			The method returns list of yaml files.
			When tenant='xxxxx'
			The method returns list of yaml files that are disabled for tenant 'xxxxx'.

			When recursive=True
			returns a list of yaml files located in zero or more directories and
			subdirectories.
			When recursive=False
			returns a list of yaml files located in /library.
		"""
		for library in self.Libraries.values():
			item = await library.list(path, tenant, recursive)
			if item is not None:
				return item
