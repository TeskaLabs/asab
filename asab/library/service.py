import re
import asyncio
import logging
import functools
import configparser

from ..abc import Service
from ..config import Config

#

L = logging.getLogger(__name__)

#


class LibraryService(Service):

	def __init__(self, app, service_name, paths=None):
		'''
		The library service is designed to "exists" in multiple instances,
		with different `paths` setup.
		For that reason, you have to provide unique `service_name`
		and there is no _default_ value for that.

		If `paths` are not provided, they are fetched from `[library]providers` configuration.
		'''

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
			await lib.finalize(self.App)


	def _create_library(self, path):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeeper://'):
			from .providers.zookeeper import ZooKeeperLibraryProvider
			library_provider = ZooKeeperLibraryProvider(self, path)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			from .providers.filesystem import FileSystemLibraryProvider
			library_provider = FileSystemLibraryProvider(self, path)

		else:
			L.error("Incorrect/unknown provider for '{}'".format(path))
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries[path] = library_provider


	def is_ready(self):
		"""
		It checks if all the libraries are ready.

		:return: A boolean value.
		"""
		return functools.reduce(
			lambda x, provider: provider.IsReady and x,
			self.Libraries.values(),
			True
		)

	def _set_ready(self, provider):
		if self.is_ready():
			L.info("Library is ready.", struct_data={'name': self.Name})
			self.App.PubSub.publish("ASABLibrary.ready!", self)


	# TODO: Read disabled from the first library and apply that on the results of `read` and `list`.


	async def read(self, path, tenant=None):
		# It must start with '/'
		if path[:1] != '/':
			path = '/' + path

		# TODO: Filter the `path` using disabled.

		for library in self.Libraries.values():
			item = await library.read(path)
			if item is None:
				continue

			return item

		return None


	async def list(self, path="/", tenant=None, recursive=False):
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

		# Normalize path

		# Path must NOT end with '/'
		while path[-1:] == '/':
			path = path[:-1]

		# Path must start with '/'
		if path[:1] != '/':
			path = '/' + path

		# List requested level using all available providers
		items = await _list(path, tenant, providers=self.Libraries.values())

		if recursive:
			# If recursive scan is requested, then iterate thru list of items
			# find 'dir' types there and list them.
			# Output of this list is attached to the list for recursive scan
			# and also to the final output
			recitems = list(items[:])

			while len(recitems) > 0:

				item = recitems.pop(0)
				if item.type != 'dir':
					continue

				child_items = await _list(item.name, tenant, providers=item.providers)
				items.extend(child_items)
				recitems.extend(child_items)

		return items


async def _list(path, tenant, providers):

	# Execute the list query in all providers in-parallel
	result = await asyncio.gather(*[
		library.list(path)
		for library in providers
	], return_exceptions=True)

	items = []
	uniq = dict()
	for ress in result:

		if isinstance(ress, KeyError):
			# The path doesn't exists in the provider
			continue

		if isinstance(ress, Exception):
			L.exception("Error when listing items from provider", exc_info=ress)
			continue

		for item in ress:

			# If the item already exists, merge it
			pitem = uniq.get(item.name)
			if pitem is not None:
				if pitem.type == 'dir' and item.type == 'dir':
					# Directories are joined
					pitem.providers.extend(item.providers)
				
				# Other item types are skipped
				continue

			# TODO: Filter the `listres` using disabled.
			uniq[item.name] = item
			items.append(item)

	items.sort(key=lambda x: x.name)

	return items
