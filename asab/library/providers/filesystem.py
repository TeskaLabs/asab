import io
import os
import os.path
import stat
import glob
import struct
import typing
import logging

from .abc import LibraryProviderABC
from ..item import LibraryItem
from ...timer import Timer
from ...contextvars import Tenant, Authz

try:
	from .filesystem_inotify import (
		inotify_init,
		inotify_add_watch,
		IN_CREATE,
		IN_ISDIR,
		IN_ALL_EVENTS,
		EVENT_FMT,
		EVENT_SIZE,
		IN_MOVED_TO,
		IN_IGNORED,
	)
except OSError:
	inotify_init = None

L = logging.getLogger(__name__)


class FileSystemLibraryProvider(LibraryProviderABC):
	"""
	Filesystem provider with ZooKeeper-like target semantics:

	- global path: <BasePath>/<path>
	- tenant path: <BasePath>/.tenants/<tenant>/<path>
	- personal path: <BasePath>/.personal/<tenant>/<credentials>/<path>

	read():
		personal → tenant → global

	list():
		personal-items + tenant-items + global-items (no merging by name)

	subscribe(path, target):
		None / "global"        -> watch global path
		"tenant"               -> watch in all tenants under /.tenants
		("tenant", "<tenant>") -> watch in one tenant
		"personal"             -> watch all personal scopes
		("personal", "<cred>") -> watch one personal credential scope
	"""

	def __init__(self, library, path, layer, *, set_ready=True):
		super().__init__(library, layer)
		# Check for `file://` prefix and strip it if present
		if path.startswith('file://'):
			path = path[7:]  # Strip "file://"

		path = os.path.abspath(path)
		self.BasePath = path.rstrip("/")

		L.info("is connected.", struct_data={'path': path})
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())

		if inotify_init is not None:
			init = inotify_init()
			if init == -1:
				L.warning(
					"Subscribing to library changes in filesystem provider is not available. Inotify was not initialized.")
				self.FD = None
			else:
				self.FD = init
				self.App.Loop.add_reader(self.FD, self._on_inotify_read)
				self.AggrTimer = Timer(self.App, self._on_aggr_timer)
		else:
			self.FD = None

		self.DisabledFilePath = os.path.join(self.BasePath, '.disabled.yaml')

		self.AggrEvents = []
		self.WDs = {}  # wd -> (subscribed_path, child_path)

	def _current_tenant_id(self):
		try:
			return Tenant.get()
		except LookupError:
			return None

	def _current_credentials_id(self):
		try:
			authz = Authz.get()
			return getattr(authz, "CredentialsId", None)
		except LookupError:
			return None

	def _personal_path(self, path, tenant_id, cred_id):
		assert path[:1] == '/'

		if not tenant_id or not cred_id:
			return None

		base = os.path.join(self.BasePath, '.personal')
		full = os.path.normpath(
			os.path.join(base, tenant_id, cred_id, path.lstrip('/'))
		)

		if not full.startswith(base + os.sep):
			raise ValueError("Path traversal detected")

		return full

	def _resolve_fs_path_from_info(self, info):
		scope = info["scope"]
		path = info["path"]
		tenant_id = info["tenant_id"]
		cred_id = info["cred_id"]

		if scope == "global":
			return self.build_path(path)

		if scope == "tenant":
			return self.build_path(path, tenant_specific=True, tenant=tenant_id)

		if scope == "personal":
			fs_path = self._personal_path(path, tenant_id, cred_id)
			if fs_path is None:
				raise RuntimeError("Personal scope path without tenant/cred")
			return fs_path

		raise RuntimeError("Unknown scope: {}".format(scope))

	async def _get_personal_scopes(self) -> typing.List[tuple[str, str]]:
		"""
		Return list of (tenant_id, cred_id) that exist under /.personal
		"""
		root = os.path.join(self.BasePath, ".personal")
		if not os.path.isdir(root):
			return []

		scopes = []
		for tenant in os.listdir(root):
			tpath = os.path.join(root, tenant)
			if tenant.startswith(".") or not os.path.isdir(tpath):
				continue
			for cred in os.listdir(tpath):
				cpath = os.path.join(tpath, cred)
				if cred.startswith(".") or not os.path.isdir(cpath):
					continue
				scopes.append((tenant, cred))
		return scopes

	def _validate_read_path(self, path: str) -> None:
		"""
		Validate a library item path for read().

		Enforces:
			- absolute path (starts with '/')
			- file extension present
			- no double slashes
		"""
		assert path[:1] == '/', "File path must start with '/' (e.g. /library/Templates/file.json)"
		assert len(
			os.path.splitext(path)[1]) > 0, "File path must end with an extension (e.g. /library/Templates/item.json)"
		assert '//' not in path, "File path cannot contain double slashes (//)"

	def build_path(self, path, tenant_specific=False, tenant=None):
		"""
		Build an absolute filesystem path under this provider base path.

		Args:
			path: Library path starting with '/'.
			tenant_specific: If True, resolve into '/.tenants/<tenant>/' when tenant is available.
			tenant: Explicit tenant ID override. If None, uses Tenant context.

		Returns:
			Absolute filesystem path.

		Notes:
			- This method is for both file and directory paths.
			- It does not enforce file-extension rules.
		"""
		assert path[:1] == '/'

		if tenant_specific:
			if tenant is None:
				try:
					tenant = Tenant.get()
				except LookupError:
					tenant = None

			if tenant:
				node_path = self.BasePath + '/.tenants/' + tenant + path
			else:
				node_path = self.BasePath + path if path != '/' else self.BasePath
		else:
			node_path = self.BasePath + path if path != '/' else self.BasePath

		node_path = node_path.rstrip("/")

		assert '//' not in node_path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"
		assert node_path[0] == '/', "Directory path must start with '/'"

		return node_path

	async def read(self, path: str) -> typing.Optional[typing.IO]:
		"""
		Read a file from filesystem overlays in precedence order:

		1) personal: '/.personal/<tenant>/<credentials>/<path>'
		2) tenant:   '/.tenants/<tenant>/<path>'
		3) global:   '<BasePath>/<path>'

		Returns:
			Binary file object, or None if not found.
		"""
		self._validate_read_path(path)

		tenant_id = self._current_tenant_id()
		cred_id = self._current_credentials_id()

		# personal
		personal_path = self._personal_path(path, tenant_id, cred_id)
		if personal_path and os.path.isfile(personal_path):
			return io.FileIO(personal_path, 'rb')

		# tenant
		try:
			tenant_path = self.build_path(path, tenant_specific=True)
			if os.path.isfile(tenant_path):
				return io.FileIO(tenant_path, 'rb')
		except Exception:
			pass

		# global
		try:
			global_path = self.build_path(path, tenant_specific=False)
			return io.FileIO(global_path, 'rb')
		except (FileNotFoundError, IsADirectoryError):
			return None

	async def list(self, path: str) -> list:
		"""
		List directory items from overlays and concatenate in precedence order:

		personal + tenant + global

		Returns:
			List[LibraryItem]
		"""
		# Global
		global_node_path = self.build_path(path, tenant_specific=False)
		global_items = self._list_from_node_path(global_node_path, path, target="global")

		# Tenant
		tenant_node_path = self.build_path(path, tenant_specific=True)
		if tenant_node_path != global_node_path:
			try:
				tenant_items = self._list_from_node_path(tenant_node_path, path, target="tenant")
			except KeyError:
				# Tenant path does not exist → empty overlay (ZooKeeper semantics)
				tenant_items = []
		else:
			tenant_items = []

		# personal
		personal_items = []
		tenant_id = self._current_tenant_id()
		cred_id = self._current_credentials_id()
		if tenant_id and cred_id:
			try:
				personal_node = self._personal_path(path, tenant_id, cred_id)
			except ValueError:
				personal_node = None

			if personal_node is not None:
				try:
					personal_items = self._list_from_node_path(
						personal_node,
						path,
						target="personal",
					)
				except KeyError:
					personal_items = []

		return personal_items + tenant_items + global_items

	def _list_from_node_path(self, node_path: str, base_path: str, target="global"):
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProviderTarget.".format(base_path))

		items = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			try:
				fstat = os.stat(fname)
			except FileNotFoundError:
				continue

			# Turn absolute filesystem path back into library path under base_path
			rel_name = os.path.basename(fname)
			if rel_name.startswith('.'):
				continue

			if stat.S_ISREG(fstat.st_mode):
				ftype = "item"
				size = fstat.st_size
				lib_name = "{}/{}".format(base_path.rstrip("/"), rel_name)
			elif stat.S_ISDIR(fstat.st_mode):
				ftype = "dir"
				size = None
				lib_name = "{}/{}/".format(base_path.rstrip("/"), rel_name)
			else:
				ftype = "?"
				size = None
				lib_name = "{}/{}".format(base_path.rstrip("/"), rel_name)

			# Remove any component that starts with '.'
			if any(x.startswith('.') for x in lib_name.split('/')):
				continue

			if self.Layer == 0:
				if target == "global":
					layer_label = "0:global"
				elif target == "tenant":
					layer_label = "0:tenant"
				elif target == "personal":
					layer_label = "0:personal"
				else:
					layer_label = "0:{}".format(target)
			else:
				layer_label = self.Layer

			items.append(LibraryItem(
				name=lib_name,
				type=ftype,
				layers=[layer_label],
				providers=[self],
				size=size,
			))

		return items

	def _list(self, path: str):
		node_path = self.BasePath + path
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProvider.".format(path))

		items = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			fstat = os.stat(fname)

			assert fname.startswith(self.BasePath)
			fname = fname[len(self.BasePath):]

			if stat.S_ISREG(fstat.st_mode):
				ftype = "item"
				size = fstat.st_size
			elif stat.S_ISDIR(fstat.st_mode):
				ftype = "dir"
				fname += '/'
				size = None
			else:
				ftype = "?"
				size = None

			if any(x.startswith('.') for x in fname.split('/')):
				continue

			items.append(LibraryItem(
				name=fname,
				type=ftype,
				layers=[self.Layer],
				providers=[self],
				size=size,
			))

		return items

	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		"""
		Subscribe to filesystem changes under `path`.

		Note:
			`target` is accepted for API compatibility; current filesystem implementation
			watches the resolved path without target-specific scoping.
		"""
		if not os.path.isdir(self.BasePath + path):
			return
		if self.FD is None:
			L.warning("Cannot subscribe to changes in the filesystem layer of the library: '{}'".format(self.BasePath))
			return
		self._subscribe_recursive(path, path)


	def _subscribe_recursive(self, subscribed_path, path_to_be_listed):
		binary = (self.BasePath + path_to_be_listed).encode()
		wd = inotify_add_watch(self.FD, binary, IN_ALL_EVENTS)
		if wd == -1:
			L.error("Error in inotify_add_watch")
			return
		self.WDs[wd] = (subscribed_path, path_to_be_listed)

		try:
			items = self._list(path_to_be_listed)
		except KeyError:
			# subscribing to non-existing directory is silent
			return

		for item in items:
			if item.type == "dir":
				self._subscribe_recursive(subscribed_path, item.name)


	def _on_inotify_read(self):
		data = os.read(self.FD, 64 * 1024)

		pos = 0
		while pos < len(data):
			wd, mask, cookie, namesize = struct.unpack_from(EVENT_FMT, data, pos)
			pos += EVENT_SIZE + namesize
			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			if mask & IN_ISDIR == IN_ISDIR and ((mask & IN_CREATE == IN_CREATE) or (mask & IN_MOVED_TO == IN_MOVED_TO)):
				subscribed_path, child_path = self.WDs[wd]
				self._subscribe_recursive(subscribed_path, "/".join([child_path, name]))

			if mask & IN_IGNORED == IN_IGNORED:
				# cleanup
				del self.WDs[wd]
				continue

			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			full_path = os.path.join(self.BasePath, name)
			if os.path.normpath(full_path) == os.path.normpath(self.DisabledFilePath):
				self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

		self.AggrTimer.restart(0.2)


	async def _on_aggr_timer(self):
		to_advertise = set()
		for wd, mask, cookie, name in self.AggrEvents:
			# When wathed directory is being removed, more than one inotify events are being produced.
			# When IN_IGNORED event occurs, respective wd is removed from self.WDs,
			# but some other events (like IN_DELETE_SELF) get to this point, without having its reference in self.WDs.
			subscribed_path, _ = self.WDs.get(wd, (None, None))
			to_advertise.add(subscribed_path)
		self.AggrEvents.clear()

		for path in to_advertise:
			if path is None:
				continue
			self.App.PubSub.publish("Library.change!", self, path)

	async def find(self, filename: str) -> list:
		"""
		Recursively search for files ending with a specific name in the file system, starting from the base path.

		:param filename: The filename to search for (e.g., '.setup.yaml')
		:return: A list of LibraryItem objects for files ending with the specified name,
				or an empty list if no matching files were found.
		"""
		results = []
		self._recursive_find(self.BasePath, filename, results)
		return results

	def _recursive_find(self, path, filename, results):
		"""
		The recursive part of the find method.

		:param path: The current path to search
		:param filename: The filename to search for
		:param results: The list where results are accumulated
		"""
		if not os.path.exists(path):
			return

		if os.path.isfile(path) and path.endswith(filename):
			item = LibraryItem(
				name=path[len(self.BasePath):],  # Store relative path
				type="item",  # or "dir" if applicable
				layers=[self.Layer],
				providers=[self],
			)
			results.append(item)
			return

		if os.path.isdir(path):
			for entry in os.listdir(path):
				full_path = os.path.join(path, entry)
				self._recursive_find(full_path, filename, results)
