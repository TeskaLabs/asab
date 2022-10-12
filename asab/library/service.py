import re
import typing
import asyncio
import logging
import functools
import configparser
import tempfile
import tarfile
import time
from io import SEEK_END, SEEK_SET

import yaml

from ..abc import Service
from ..config import Config
from ..log import LOG_NOTICE

#

L = logging.getLogger(__name__)

#


class LibraryService(Service):
	'''
	ASAB library (aka LibraryService) is an abstration for unified filesystem-like access to resources.
	In the cluster/cloud microservice architectures, it is imperative that all microservices have access to unified resources.
	There are technologies such as Apache Zookeeper that provides means for it.

	ASAB library builts on top of this concept and brings that into the ASAB microservice.

	ASAB library is designed to be read-only.
	It also allows to "stack" various libraries into one view (overlayed) that merges content of each library into one united space.

	Configuration:

	```
	[library]
	providers:
		provider+1://
		provider+2://
		provider+3://
	```

	The order of providers *IS* important, the priority (or layering) is top-down.

	Each library provider is specified by URL/URI schema:

	* `zk://` or `zookeeper://` for ZooKeeper provider
	* `file://` or local path for FileSystem provider
	* `azure+https://` for Microsoft Azure Storage provider.

	The first provider is also responsible for providing `/.disabled.yaml` that controls a visibility of items.
	If `/.disabled.yaml` is not present, then is considered empty.

	A library is created in "not ready" state, each provider then inform library when it is ready (eg. Zookeeper provider needs to connect to Zookeeper servers).
	Only after all providers are ready, the library itself become ready.
	The library indicates that by the PubSub event `ASABLibrary.ready!`.

	'''

	def __init__(self, app, service_name, paths=None):
		'''
		The library service is designed to "exists" in multiple instances,
		with different `paths` setup.
		For that reason, you have to provide unique `service_name`
		and there is no _default_ value for that.

		If `paths` are not provided, they are fetched from `[library]providers` configuration.
		'''

		super().__init__(app, service_name)
		self.Libraries = list()
		self.Disabled = {}

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
		app.PubSub.subscribe("Application.tick/60!", self.on_tick)


	async def finalize(self, app):
		while len(self.Libraries) > 0:
			lib = self.Libraries.pop(-1)
			await lib.finalize(self.App)

	async def on_tick(self, message_type):
		await self._read_disabled()



	def _create_library(self, path):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeeper://'):
			from .providers.zookeeper import ZooKeeperLibraryProvider
			library_provider = ZooKeeperLibraryProvider(self, path)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			from .providers.filesystem import FileSystemLibraryProvider
			library_provider = FileSystemLibraryProvider(self, path)

		elif path.startswith('azure+https://'):
			from .providers.azurestorage import AzureStorageLibraryProvider
			library_provider = AzureStorageLibraryProvider(self, path)

		elif path.startswith('git+'):
			from .providers.git import GitLibraryProvider
			library_provider = GitLibraryProvider(self, path)

		elif path == '' or path.startswith("#") or path.startswith(";"):
			# This is empty or commented line
			return

		else:
			L.error("Incorrect/unknown provider for '{}'".format(path))
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries.append(library_provider)


	def is_ready(self):
		"""
		It checks if all the libraries are ready.

		:return: A boolean value.
		"""
		return functools.reduce(
			lambda x, provider: provider.IsReady and x,
			self.Libraries,
			True
		)

	async def _set_ready(self, provider):
		if provider == self.Libraries[0]:
			await self._read_disabled()

		if self.is_ready():
			L.log(LOG_NOTICE, "is ready.", struct_data={'name': self.Name})
			self.App.PubSub.publish("ASABLibrary.ready!", self)


	async def read(self, path: str, tenant: str = None) -> typing.IO:
		"""
		Read the content of the library item specified by `path`.
		`None` is returned if the item is not found in the library.

		If the item is disabled (globally or for specified tenant) then None is returned.

		Example of use:

		```
		itemio = await library.read('/path', 'tenant')
		if itemio is not None:
			with itemio:
				return itemio.read()
		```

		:param path: The path to the file, `LibraryItem.name` can be used directly
		:param tenant: The tenant to apply. If not specified, the global access is assumed
		:return: I/O stream (read) with the content of the libary item.
		"""
		# It must start with '/'
		if path[:1] != '/':
			path = '/' + path

		if self.check_disabled(path, tenant=tenant):
			return None

		for library in self.Libraries:
			itemio = await library.read(path)
			if itemio is None:
				continue
			return itemio

		return None


	async def list(self, path="/", tenant=None, recursive=False):
		"""
		List the directory of the library specified by the path.
		It returns a list of `LibraryItem` entris.

		Tenant is an optional parameter to list method for "disable" evaluation.
			and default recursive is False.

		When tenant=None
			The method returns list of items that are enabled (not disabled).

		When tenant='xxxxx'
			The method returns list of items that are enabled (not disabled) for tenant 'xxxxx'.

		When recursive=True
			The method returns list of items that are located at `path` and in subdirectories of that location.

		When recursive=False
			The method returns list of items that are located at `path`
		"""

		# Normalize path

		# Path must NOT end with '/'
		while path[-1:] == '/':
			path = path[:-1]

		# Path must start with '/'
		if path[:1] != '/':
			path = '/' + path

		# List requested level using all available providers
		items = await self._list(path, tenant, providers=self.Libraries)

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

				child_items = await self._list(item.name, tenant, providers=item.providers)
				items.extend(child_items)
				recitems.extend(child_items)

		return items


	async def _list(self, path, tenant, providers):

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

				item.disabled = self.check_disabled(item.name, tenant=tenant)

				# If the item already exists, merge it
				pitem = uniq.get(item.name)
				if pitem is not None:
					if pitem.type == 'dir' and item.type == 'dir':
						# Directories are joined
						pitem.providers.extend(item.providers)

					# Other item types are skipped
					continue

				uniq[item.name] = item
				items.append(item)

		items.sort(key=lambda x: x.name)

		return items


	async def _read_disabled(self):
		# `.disabled.yaml` is read from the first configured library
		# It is applied on all libraries in the configuration.
		disabled = await self.Libraries[0].read('/.disabled.yaml')
		if disabled is None:
			self.Disabled = {}
		else:
			try:
				self.Disabled = yaml.safe_load(disabled)
				if self.Disabled is None:
					self.Disabled = {}
				else:
					assert (isinstance(self.Disabled, dict))
			except Exception:
				self.Disabled = {}
				L.exception("Failed to parse '/.disabled.yaml'")


	def check_disabled(self, path, tenant=None):
		"""
		If the item is disabled for everybody, or if the item is disabled for the specified tenant, then
		return True. Otherwise, return False

		:param path: The path to the item
		:param tenant: The tenant name
		:return: Boolean
		"""

		disabled = self.Disabled.get(path)
		if disabled is None:
			return False

		if disabled == '*':
			# Item is disabled for everybody
			return True

		if tenant is not None and tenant in disabled:
			# Item is disabled for a specified tenant
			return True

		return False


	async def export(self, path="/", tenant=None):

		fileobj = tempfile.TemporaryFile()
		tarobj = tarfile.open(name=None, mode='w:gz', fileobj=fileobj)

		while path[-1:] == '/':
			path = path[:-1]

		# Path must start with '/'
		if path[:1] != '/':
			path = '/' + path

		# List requested level using all available providers
		only_first = [self.Libraries[0]]
		items = await self._list(path, tenant, providers=only_first)

		recitems = list(items[:])

		while len(recitems) > 0:

			item = recitems.pop(0)
			if item.type != 'dir':
				continue

			child_items = await self._list(item.name, tenant, providers=item.providers)
			items.extend(child_items)
			recitems.extend(child_items)

		for item in items:
			if item.type != 'item':
				continue
			my_data = await self.Libraries[0].read(item.name)
			info = tarfile.TarInfo(item.name)
			my_data.seek(0, SEEK_END)
			info.size = my_data.tell()
			my_data.seek(0, SEEK_SET)
			info.mtime = time.time()
			tarobj.addfile(tarinfo=info, fileobj=my_data)

		tarobj.close()
		fileobj.seek(0)
		return fileobj
