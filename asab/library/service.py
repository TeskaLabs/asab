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
		paths = Config["library"]["providers"]
		self.Libraries = dict()
		for path in re.split(r"\s+", paths):
			self._create_library(path)

	def _create_library(self, path):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeeper://'):
			library_provider = ZooKeeperLibraryProvider(self.App, path)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			library_provider = FileSystemLibraryProvider(self.App, path)

		self.Libraries[path] = library_provider


	async def read(self, path):
		for library in self.Libraries.values():
			item = await library.read(path)
			if item is not None:
				return item

	async def list(self, path, recursive=True):
		for library in self.Libraries.values():
			item = await library.list(path, recursive)
			if item is not None:
				return item
