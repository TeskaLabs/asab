import re
import io
import time
import os.path
import typing
import tarfile
import asyncio
import logging
import tempfile
import functools
import configparser
import contextlib

import yaml

from ..abc import Service
from ..config import Config
from ..log import LOG_NOTICE
from .item import LibraryItem
from ..application import Application
from .providers.abc import LibraryProviderABC
from ..exceptions import LibraryInvalidPathError
from ..contextvars import Tenant

#

L = logging.getLogger(__name__)
LogObsolete = logging.getLogger("OBSOLETE")

#


class LibraryService(Service):
	"""
	Configuration:

	```ini
	[library]
	providers:
		provider+1://
		provider+2://
		provider+3://
	```

	The order of providers is important, the priority (or layering) is top-down.

	Each library provider is specified by URL/URI schema:

	* `zk://` or `zookeeper://` for ZooKeeper provider
	* `file://` or local path for FileSystem provider
	* `azure+https://` for Microsoft Azure Storage provider.
	* `git+https://` for Git provider.
	* `libsreg+https://` for Libraries provider.

	The first provider is responsible for providing `/.disabled.yaml`.

	A library is created in “not ready” state, each provider then informs the library when it is ready
	(eg. Zookeeper provider needs to connect to Zookeeper servers). Only after all providers are ready, the library itself becomes ready.
	The library indicates that by the PubSub event `Library.ready!`.
	"""

	def __init__(self, app: Application, service_name: str, paths: typing.Union[str, typing.List[str], None] = None):
		"""
		Initialize the LibraryService.

		The library service is designed to "exist" in multiple instances,
		with different `paths` setups.
		For that reason, you have to provide unique `service_name`
		and there is no _default_ value for that.

		If `paths` are not provided, they are fetched from `[library]providers` configuration.

		Args:
			app: The ASAB Application.
			service_name: A unique name of the service.
			paths (str | list[str] | None ): Either single path or list of paths with which LibraryService is connected.
		"""

		super().__init__(app, service_name)
		self.Libraries: list[LibraryProviderABC] = []
		self.Disabled: dict = {}
		self.DisabledPaths: list = []

		if paths is None:
			# load them from configuration
			try:
				paths = Config.getmultiline("library", "providers")
			except configparser.NoOptionError:
				L.critical("'providers' option is not present in configuration section 'library'.")
				raise SystemExit("Exit due to a critical configuration error.")

		# paths can be string if specified as argument
		if isinstance(paths, str):
			paths = re.split(r"\s+", paths)

		for layer, path in enumerate(paths):
			# Create library for each layer of paths
			self._create_library(path, layer)

		app.PubSub.subscribe("Application.tick/60!", self._on_tick60)


	async def finalize(self, app):
		while len(self.Libraries) > 0:
			lib = self.Libraries.pop(-1)
			await lib.finalize(self.App)

	async def _on_tick60(self, message_type):
		await self._read_disabled()

	def _create_library(self, path, layer):
		library_provider = None
		if path.startswith('zk://') or path.startswith('zookeeper://'):
			from .providers.zookeeper import ZooKeeperLibraryProvider
			library_provider = ZooKeeperLibraryProvider(self, path, layer)

		elif path.startswith('./') or path.startswith('/') or path.startswith('file://'):
			from .providers.filesystem import FileSystemLibraryProvider
			library_provider = FileSystemLibraryProvider(self, path, layer)

		elif path.startswith('azure+https://'):
			from .providers.azurestorage import AzureStorageLibraryProvider
			library_provider = AzureStorageLibraryProvider(self, path, layer)

		elif path.startswith('git+'):
			from .providers.git import GitLibraryProvider
			library_provider = GitLibraryProvider(self, path, layer)

		elif path.startswith('libsreg+'):
			from .providers.libsreg import LibsRegLibraryProvider
			library_provider = LibsRegLibraryProvider(self, path, layer)

		elif path == '' or path.startswith("#") or path.startswith(";"):
			# This is empty or commented line
			return

		else:
			L.error("Incorrect/unknown provider for '{}'".format(path))
			raise SystemExit("Exit due to a critical configuration error.")

		self.Libraries.append(library_provider)

	def is_ready(self) -> bool:
		"""
		Check if all the libraries are ready.

		Returns:
			True if all libraries are ready, otherwise False.
		"""
		if len(self.Libraries) == 0:
			return False

		return functools.reduce(
			lambda x, provider: provider.IsReady and x,
			self.Libraries,
			True
		)

	async def _set_ready(self, provider):
		if len(self.Libraries) == 0:
			return

		if (provider == self.Libraries[0]) and provider.IsReady:
			await self._read_disabled()

		if self.is_ready():
			L.log(LOG_NOTICE, "is ready.", struct_data={'name': self.Name})
			self.App.PubSub.publish("Library.ready!", self)
		elif not provider.IsReady:
			L.log(LOG_NOTICE, "is NOT ready.", struct_data={'name': self.Name})
			self.App.PubSub.publish("Library.not_ready!", self)

	async def find(self, path: str) -> typing.Optional[typing.List[str]]:
		"""
		Searches for files with a specific name within a library, using the provided path.

		The method traverses the library directories, looking for files that match the given filename.
		It returns a list of paths leading to these files, or `None` if no such files are found.

		Args:
			path (str): The path specifying the filename and its location within the library.
						The path should start with a forward slash and include the filename.
						Example: '/library/Templates/.setup.yaml'

		Returns:
			typing.Optional[typing.List[str]]: A list containing the paths to the found files,
											`or an `empty list` if no files are found that match the filename.
		"""
		_validate_path_item(path)

		results = []
		for library in self.Libraries:
			found_files = await library.find(path)
			if found_files:
				results.extend(found_files)

		return results

	async def read(self, path: str) -> typing.Optional[typing.IO]:
		"""
		THIS IS OBSOLETED METHOD, USE `open(...)` !!!

		Read the content of the library item specified by `path`. This method can be used only after the Library is ready.

		Args:
			path (str): Path to the file, `LibraryItem.name` can be used directly.
			tenant (str | None): The tenant to apply. If not specified, the global access is assumed.

		Returns:
			( IO | None ): Readable stream with the content of the library item. `None` is returned if the item is not found or if it is disabled (either globally or for the specified tenant).

		Example:

		```python
		itemio = await library.read('/path', 'tenant')
		if itemio is not None:
			with itemio:
				return itemio.read()
		```
		"""

		LogObsolete.warning("Method 'LibraryService.read()' is obsolete. Use 'LibraryService.open()' method instead.")
		_validate_path_item(path)

		if self.check_disabled(path):
			return None

		for library in self.Libraries:
			itemio = await library.read(path)
			if itemio is None:
				continue
			return itemio

		return None


	@contextlib.asynccontextmanager
	async def open(self, path: str):
		"""
		Read the content of the library item specified by `path` in a SAFE way, protected by a context manager/with statement.
		This method can be used only after the Library is ready.

		Example:

		```python
		async with self.App.LibraryService.open(path) as b:
			if b is None:
				return None

			text = b.read().decode("utf-8")
		```
		"""

		_validate_path_item(path)

		# Same functionality as in read() method
		itemio = None
		disabled = self.check_disabled(path)
		if not disabled:
			for library in self.Libraries:
				itemio = await library.read(path)
				if itemio is not None:
					break

		if itemio is None:
			yield itemio
		else:
			try:
				yield itemio
			finally:
				itemio.close()


	async def list(self, path: str = "/", recursive: bool = False) -> typing.List[LibraryItem]:
		"""
		List the directory of the library specified by the path that are enabled for the specified tenant. This method can be used only after the Library is ready.

		Args:
			path (str): Path to the directory.
			tenant (str | None): If specified, items that are enabled for the tenant are filtered.
			recursive (bool): If `True`, return a list of items located at `path` and its subdirectories.

		Returns:
			List of items that are enabled for the tenant.
		"""

		_validate_path_directory(path)

		# List requested level using all available providers
		items = await self._list(path, providers=self.Libraries)

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

				child_items = await self._list(item.name, providers=item.providers)
				items.extend(child_items)
				recitems.extend(child_items)
		return items

	async def _list(self, path, providers):
		"""
		Lists items from all providers and applies layer precedence,
		ensuring that layers are tracked accurately for each item.

		Args:
			path (str): The path to list items from.
			providers (list): A list of providers to query.

		Returns:
			list: A sorted list of unique LibraryItem objects.
		"""
		items: list[LibraryItem] = []
		unique_items: dict[str, LibraryItem] = {}

		# List items from every provider concurrently, while tracking their layers
		tasks = [(layer, asyncio.create_task(provider.list(path))) for layer, provider in enumerate(providers)]

		# Process tasks as they complete, ensuring layer precedence is correctly applied
		for layer, task in tasks:
			try:
				items_list_from_provider: list[LibraryItem] = await task
			except KeyError:
				# The path doesn't exist in the provider
				continue
			except Exception:
				L.exception("Unexpected error when listing path '{}' on layer {}.".format(path, layer))
				continue

			for item in items_list_from_provider:
				item.disabled = self.check_disabled(item.name)

				# Check if the item already exists
				pitem = unique_items.get(item.name)

				if pitem is not None:
					# Merge directories (if both are 'dir')
					if pitem.type == "dir" and item.type == "dir":
						# Merge providers for the directory
						pitem.providers.extend(item.providers)

					# Replace lower-priority items
					elif pitem.type == item.type and item.layer < pitem.layer:
						# Replace with the higher-priority item
						unique_items[item.name] = item
						items = [unique_items[x.name] if x.name == item.name else x for x in items]

				else:
					# New item: Assign it to unique_items
					unique_items[item.name] = item
					items.append(item)

		# Sort items by name
		items.sort(key=lambda x: x.name)
		return items

	async def _read_disabled(self):
		# `.disabled.yaml` is read from the first configured library
		# It is applied on all libraries in the configuration.
		disabled = await self.Libraries[0].read('/.disabled.yaml')

		if disabled is None:
			self.Disabled = {}
			self.DisabledPaths = []
			return

		try:
			disabled = yaml.load(disabled, Loader=yaml.CSafeLoader)
		except Exception:
			self.Disabled = {}
			self.DisabledPaths = []
			L.exception("Failed to parse '/.disabled.yaml'")
			return

		if disabled is None:
			self.Disabled = {}
			self.DisabledPaths = []
			return

		if isinstance(disabled, set):
			# This is for a backward compatibility (Aug 2023)
			self.Disabled = {key: '*' for key in self.Disabled}
			self.DisabledPaths = []
			return

		self.Disabled = {}
		self.DisabledPaths = []
		for k, v in disabled.items():
			if k.endswith('/'):
				self.DisabledPaths.append((k, v))
			else:
				self.Disabled[k] = v

		# Sort self.DisabledPaths from the shortest to longest
		self.DisabledPaths.sort(key=lambda x: len(x[0]))


	def check_disabled(self, path: str) -> bool:
		"""
		Check if the item specified in path is disabled, either globally or for the specified tenant.

		Args:
			path (str): Path to the item to be checked.
			tenant (str | None): The tenant to apply. If not specified, the global access is assumed.

		Returns:
			`True` if the item is disabled for the tenant.
		"""
		if not isinstance(path, str) or not path:
			raise LibraryInvalidPathError(
				message="Argument 'path' must be a non-empty string.",
				path=path,
			)
		try:
			tenant = Tenant.get()
		except LookupError:
			tenant = None

		# First check disabled by path
		for dp, disabled in self.DisabledPaths:
			if path.startswith(dp):
				if '*' in disabled:
					# Path is disabled for everybody
					return True

				if tenant is not None and tenant in disabled:
					# Path is disabled for a specified tenant
					return True

		# Then check for a specific item entries

		disabled = self.Disabled.get(path)

		if disabled is None:
			return False

		if '*' in disabled:
			# Item is disabled for everybody
			return True

		if tenant is not None and tenant in disabled:
			# Item is disabled for a specified tenant
			return True

		return False

	async def export(self, path: str = "/", remove_path: bool = False) -> typing.IO:
		"""
		Return a file-like stream containing a gzipped tar archive of the library contents of the path.

		Args:
			path: The path to export.
			tenant (str | None ): The tenant to use for the operation.
			remove_path: If `True`, the path will be removed from the tar file.

		Returns:
			A file object containing a gzipped tar archive.
		"""

		_validate_path_directory(path)

		fileobj = tempfile.TemporaryFile()
		tarobj = tarfile.open(name=None, mode='w:gz', fileobj=fileobj)

		items = await self._list(path, providers=self.Libraries[:1])
		recitems = list(items[:])

		while len(recitems) > 0:

			item = recitems.pop(0)
			if item.type != 'dir':
				continue

			child_items = await self._list(item.name, providers=item.providers)
			items.extend(child_items)
			recitems.extend(child_items)

		for item in items:
			if item.type != 'item':
				continue
			my_data = await self.Libraries[0].read(item.name)
			if remove_path:
				assert item.name.startswith(path)
				tar_name = item.name[len(path):]
			else:
				tar_name = item.name
			info = tarfile.TarInfo(tar_name)
			my_data.seek(0, io.SEEK_END)
			info.size = my_data.tell()
			my_data.seek(0, io.SEEK_SET)
			info.mtime = time.time()
			tarobj.addfile(tarinfo=info, fileobj=my_data)

		tarobj.close()
		fileobj.seek(0)
		return fileobj


	async def subscribe(
		self,
		paths: typing.Union[str, typing.List[str]],
		target: typing.Union[str, tuple, None] = None,
	) -> None:
		"""
		Subscribe to changes for specified paths of the library.

		In order to notify on changes in the Library, this method must be used after the Library is ready.

		Args:
			paths (str | list[str]): Either single path or list of paths to be subscribed. All the paths must be absolute (start with '/').
			target: In which target to watch the changes. Possible values:
				- "global" to watch global path changes
				- "tenant" to watch path changes in tenants
				- ("tenant", TENANT_ID) to watch path changes in one specified tenant TENANT_ID

		Examples:
		```python
		class MyApplication(asab.Application):

			async def initialize(self):
				self.PubSub.subscribe("Library.ready!", self.on_library_ready
				self.PubSub.subscribe("Library.change!", self.on_library_change)

			async def on_library_ready(self, event_name, library=None):
				await self.LibraryService.subscribe(["/alpha","/beta"])

			def on_library_change(self, message, provider, path):
				print("New changes in the library found by provider: '{}'".format(provider))

		```
		"""
		if isinstance(paths, str):
			paths = [paths]
		for path in paths:
			if not path.startswith("/"):
				raise LibraryInvalidPathError(
					message="Directory path must start with '/' when subscribing to Library changes.",
					path=path,
				)

			for provider in self.Libraries:
				await provider.subscribe(path, target)


def _validate_path_item(path: str) -> None:
	# File path must start with '/'
	if not path.startswith("/"):
		raise LibraryInvalidPathError(
			message="Item path must start with '/' (e.g. '/Templates/item.json')",
			path=path,
		)

	# File path must end with extension (e.g. '.json')
	if not len(os.path.splitext(path)[1]) > 0:
		raise LibraryInvalidPathError(
			message="Item path must end with an extension (e.g. '/Templates/item.json')",
			path=path,
		)

	if ".." in path:
		raise LibraryInvalidPathError(
			message="Item path cannot contain '..'",
			path=path,
		)

	if "~" in path:
		raise LibraryInvalidPathError(
			message="Item path cannot contain '~'",
			path=path,
		)


def _validate_path_directory(path: str) -> None:
	# Directory path must start with '/'
	if not path.startswith("/"):
		raise LibraryInvalidPathError(
			message="Directory path must start with '/' (e.g. '/Templates/Email/')",
			path=path,
		)

	# Directory path must end with '/'
	if not path.endswith("/"):
		raise LibraryInvalidPathError(
			message="Directory path must end with '/' (e.g. '/Templates/Email/')",
			path=path,
		)

	# Directory path cannot contain '//'
	if "//" in path:
		raise LibraryInvalidPathError(
			message="Directory path cannot contain '//' (e.g. '/Templates/Email/')",
			path=path,
		)

	if ".." in path:
		raise LibraryInvalidPathError(
			message="Directory path cannot contain '..'",
			path=path,
		)

	if "~" in path:
		raise LibraryInvalidPathError(
			message="Directory path cannot contain '~'",
			path=path,
		)
