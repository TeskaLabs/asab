import re
import io
import time
import os.path
import typing
import tarfile
import asyncio
import logging
import tempfile
import configparser
import contextlib

import yaml

from ..abc import Service
from ..config import Config
from ..log import LOG_NOTICE
from .item import LibraryItem
from ..application import Application
from .providers.abc import LibraryProviderABC
from ..exceptions import LibraryInvalidPathError, LibraryNotReadyError
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

	def __init__(
		self,
		app: Application,
		service_name: str,
		paths: typing.Union[str, typing.List[str], None] = None
	):
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
		Check if all the library providers are ready.

		Returns:
			True if every provider is ready; if even one provider is not, returns False.
		"""
		if not self.Libraries:
			return False

		for provider in self.Libraries:
			if not provider.IsReady:
				return False
		return True


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

	def _ensure_ready(self):
		if not self.is_ready():
			raise LibraryNotReadyError("Library is not ready yet.")

	async def find(self, path: str) -> typing.List[str]:
		"""
		Search for files with a specific name within a library, using the provided path.

		The method traverses the library directories, looking for files that match the given filename.
		It returns a list of paths leading to these files, empty if no items are found.

		Args:
			path (str): Location of the file in Library. It must start with a forward slash and include the filename. Example: '/Dashboards/Cisco/Overview.json'

		Returns:
			typing.List[str]: A list of paths to the found files. If no files are found, the list will be empty.
		"""

		self._ensure_ready()

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
		async with self.LibraryService.open(path) as io:
			if io is None:
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
		List the directory of the library specified by the path that are enabled for the specified tenant.
		This method can be used only after the Library is ready.

		**WARNING:** Tenant must be set in the context variable!
		If it is not set automatically (e.g. from web request), it must be set manually.

		Example:

		```python
		try:
			tenant_ctx = asab.contextvars.Tenant.set(tenant)
			items = self.LibraryService.list(path)
			...
		finally:
			asab.contextvars.Tenant.reset(tenant_ctx)
		```

		Args:
			path (str): Path to the directory.
			recursive (bool): If `True`, return a list of items located at `path` and its subdirectories.

		Returns:
			List of items that are enabled for the tenant.
		"""
		self._ensure_ready()

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
		Lists items from all providers, merging items with the same name,
		and simply adding every layer an item belongs to.

		Args:
			path (str): The path to list items from.
			providers (list): A list of providers to query.

		Returns:
			list: A list of unique LibraryItem objects with merged layers.
		"""
		items: list[LibraryItem] = []
		unique_items: dict[str, LibraryItem] = {}

		# Launch tasks to list items from each provider.
		tasks = [(self.Libraries.index(provider), asyncio.create_task(provider.list(path))) for provider in providers]

		for outer_layer, task in tasks:
			try:
				provider_items: list[LibraryItem] = await task
			except KeyError:
				# The path doesn't exist in this provider.
				continue
			except Exception:
				L.exception("Unexpected error when listing path '{}' on layer {}.".format(path, outer_layer))
				continue

			for item in provider_items:
				# Check if the item is disabled.
				item.disabled = self.check_disabled(item.name)
				# Use the layers as provided by the provider; if empty, fall back to outer_layer.
				provider_layers = item.layers if item.layers else [outer_layer]

				if item.name in unique_items:
					existing_item = unique_items[item.name]
					# Merge providers for directories (avoid duplicates).
					if existing_item.type == "dir" and item.type == "dir":
						for p in item.providers:
							if p not in existing_item.providers:
								existing_item.providers.append(p)
					# Extend the layers list by adding each new layer (without sorting).
					for layer_value in provider_layers:
						if layer_value not in existing_item.layers:
							existing_item.layers.append(layer_value)
				else:
					# New item: use the provided layers.
					item.layers = provider_layers
					unique_items[item.name] = item
					items.append(item)

		# Do not sort items; return them in the order they were merged.
		return items

	async def _read_disabled(self, publish_changes=False):
		old_disabled = self.Disabled.copy()
		old_disabled_paths = list(self.DisabledPaths)
		# Read the file
		disabled_file = await self.Libraries[0].read('/.disabled.yaml')

		if disabled_file is None:
			self.Disabled = {}
			self.DisabledPaths = []
		else:
			try:
				disabled_data = yaml.load(disabled_file, Loader=yaml.CSafeLoader)
			except Exception:
				L.exception("Failed to parse '/.disabled.yaml'")
				self.Disabled = {}
				self.DisabledPaths = []
				return

			if disabled_data is None:
				self.Disabled = {}
				self.DisabledPaths = []
				return

			if isinstance(disabled_data, set):
				# Backward compatibility (August 2023)
				self.Disabled = {key: '*' for key in disabled_data}
				self.DisabledPaths = []
			else:
				self.Disabled = {}
				self.DisabledPaths = []
				for k, v in disabled_data.items():
					if k.endswith('/'):
						self.DisabledPaths.append((k, v))
					else:
						self.Disabled[k] = v

		self.DisabledPaths.sort(key=lambda x: len(x[0]))

		# If requested, compare old and new disables to notify subscribers via Library.change!
		if publish_changes:
			await self._publish_change_for_disabled_diff(old_disabled, old_disabled_paths)

	async def _publish_change_for_disabled_diff(self, old_disabled, old_disabled_paths):
		"""
		Compare old and new disabled data and publish Library.change!
		if any subscribed path is affected for the specific subscription target.
		"""

		if not self.Libraries:
			return

		# Only the first provider (layer 0) owns and manages '/.disabled.yaml',
		# so all disable‐and‐subscription logic is driven from that topmost layer.
		provider = self.Libraries[0]

		# Check if the provider has Subscriptions attribute
		subscriptions = getattr(provider, "Subscriptions", None)
		if subscriptions is None:
			return

		# For each subscription (path + target)
		for p_target, p_path in subscriptions:
			# Check if something disabled under this path and target changed
			changed = self._is_disabled_diff_affecting_path(p_path, old_disabled, old_disabled_paths, p_target)

			if changed:
				self.App.PubSub.publish("Library.change!", self, p_path)

	def _is_disabled_diff_affecting_path(self, sub_path, old_disabled, old_disabled_paths, target=None):
		"""
		Check if disabling changes affect the subscribed path for a specific target.
		For target=="tenant" (wildcard), we fire whenever the set of tenants changes.
		"""

		# Normalize path (ensure it ends with / for folders)
		if not sub_path.endswith('/'):
			sub_path = sub_path + '/'

		# 1) File-level disables
		for path in old_disabled.keys() | self.Disabled.keys():
			if not path.startswith(sub_path):
				continue

			old_entry = old_disabled.get(path) or []
			new_entry = self.Disabled.get(path) or []

			if target == "tenant":
				# Wildcard tenant subscription: any change in the list of tenants
				if set(old_entry) != set(new_entry):
					return True
			else:
				old_flag = self._is_disabled_for_target(old_entry, target)
				new_flag = self._is_disabled_for_target(new_entry, target)
				if old_flag != new_flag:
					return True

		# 2) Folder-level disables
		old_map = {p: v for p, v in old_disabled_paths}
		new_map = {p: v for p, v in self.DisabledPaths}

		for path in old_map.keys() | new_map.keys():
			if not path.startswith(sub_path):
				continue

			old_entry = old_map.get(path) or []
			new_entry = new_map.get(path) or []

			if target == "tenant":
				if set(old_entry) != set(new_entry):
					return True
			else:
				old_flag = self._is_disabled_for_target(old_entry, target)
				new_flag = self._is_disabled_for_target(new_entry, target)
				if old_flag != new_flag:
					return True

		return False

	def _is_disabled_for_target(self, disabled_entry, target):
		"""
		Check if a disabled entry affects a specific target (global, tenant, or tenant ID).
		"""
		if disabled_entry is None:
			return False

		if target is None or target == "global":
			return "*" in disabled_entry

		if target == "tenant":
			# Wildcard tenant subscription (all tenants)
			return bool(disabled_entry)

		if isinstance(target, tuple) and target[0] == "tenant":
			tenant_id = target[1]
			return "*" in disabled_entry or tenant_id in disabled_entry

		return False


	def check_disabled(self, path: str) -> bool:
		"""
		Check if the item specified in path is disabled, either globally or for the specified tenant.

		**WARNING:** When checking for items disabled for a tenant,
		it must be set in context variable before using this function!
		If it is not set automatically (e.g. from web request), it must be set manually.

		Example:

		1. Is path disabled for a specific tenant?

			```python
			try:
				tenant_ctx = asab.contextvars.Tenant.set(tenant)
				disabled = self.LibraryService.check_disabled(path)
				...
			finally:
				asab.contextvars.Tenant.reset(tenant_ctx)
			```

		2. Is path disabled globally?

			```python
			disabled = self.LibraryService.check_disabled(path)
			```

		Args:
			path (str): Path to the item to be checked.

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

	async def get_item_metadata(self, path: str) -> typing.Optional[dict]:
		"""
		Retrieve metadata for a specific file in the library, including its `target`.

		Args:
			path (str): The absolute path of the file to retrieve metadata for.
						Must start with '/' and include a filename with an extension.

		Returns:
			dict: Metadata for the specified file, including `target`, or None if not found.
		"""

		# Validate the path format
		_validate_path_item(path)

		# Split into directory and filename
		directory, filename = os.path.split(path)

		if not directory or not filename:
			L.warning("Invalid path '{}': missing directory or filename.".format(path))
			return None
		# Ensure directory ends with '/'
		if not directory.endswith('/'):
			directory += '/'

		try:
			# Fetch all items in the directory
			items = await self.list(directory)
		except Exception as e:
			L.warning("Failed to list items in directory '{}': {}".format(directory, e))
			return None

		# Use dictionary for faster lookup
		items_dict = {item.name: item for item in items}

		# Retrieve the item by path
		item = items_dict.get(path)
		if item and item.type == "item":
			# Match found; return metadata including `target`
			return {
				"name": item.name,
				"type": item.type,
				"layers": item.layers,
				"providers": item.providers,
				"disabled": item.disabled,
				"override": item.override,
			}

		# Item not found
		L.info("Item '{}' not found in directory '{}'.".format(filename, directory))
		return None


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
		self._ensure_ready()

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
				await self.LibraryService.subscribe(["/path1/","/path2/"])

			def on_library_change(self, message, provider, path):
				print("New changes in the library found by provider: '{}'".format(provider))
		```
		"""
		self._ensure_ready()

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
