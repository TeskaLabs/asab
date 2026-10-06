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

# Only import context vars in the full provider, not base
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


class SimpleFileSystemLibraryProvider(LibraryProviderABC):
	"""
	Simple filesystem provider with only global path support.
	Serves as a base class for other providers that don't need
	multi-tenancy or disabled file functionality.

	- global path: <BasePath>/<path>
	"""

	def __init__(self, library, path, layer, *, source, set_ready=True, enable_inotify=True):
		super().__init__(library, layer, source)

		# Check for `file://` prefix and strip it if present
		if path.startswith('file://'):
			path = path[7:]  # Strip "file://"

		path = os.path.abspath(path)
		self.BasePath = path.rstrip("/")

		L.info("is connected.", struct_data={'path': path})
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())

		self.AggrEvents = []
		self.WDs = {}  # wd -> (subscribed_path, child_path)

		# Initialize inotify for subscription support (optional in base class).
		# Providers that treat content as nearly constant (e.g. libsreg pull) can disable it.
		if enable_inotify and inotify_init is not None:
			init = inotify_init()
			if init == -1:
				L.warning(
					"Filesystem library change notifications are unavailable; inotify initialization failed.",
					struct_data={"base_path": self.BasePath},
				)
				self.FD = None
			else:
				self.FD = init
				self.App.Loop.add_reader(self.FD, self._on_inotify_read)
				self.AggrTimer = Timer(self.App, self._on_aggr_timer)
		else:
			self.FD = None


	async def finalize(self, app):
		if self.FD is not None:
			self.App.Loop.remove_reader(self.FD)
			os.close(self.FD)


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


	def build_path(self, path):
		"""
		Build an absolute filesystem path under this provider base path.

		Args:
			path: Library path starting with '/'.

		Returns:
			Absolute filesystem path.

		Notes:
			- This method is for both file and directory paths.
			- It does not enforce file-extension rules.
		"""
		assert path[:1] == '/'

		node_path = self.BasePath + path if path != '/' else self.BasePath
		node_path = node_path.rstrip("/")

		assert '//' not in node_path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"
		assert node_path[0] == '/', "Directory path must start with '/'"

		return node_path


	async def read(self, path: str) -> typing.Optional[typing.IO]:
		"""
		Read a file from global filesystem path.

		Returns:
			Binary file object, or None if not found.
		"""
		self._validate_read_path(path)

		global_path = self.build_path(path)
		try:
			return io.FileIO(global_path, 'rb')
		except (FileNotFoundError, IsADirectoryError):
			return None


	async def list(self, path: str) -> list:
		"""
		List directory items from global path only.

		Returns:
			List[LibraryItem]
		"""
		global_node_path = self.build_path(path)
		return self._list_from_node_path(global_node_path, path)


	def _list_from_node_path(self, node_path: str, base_path: str):
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProvider.".format(base_path))

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

			items.append(LibraryItem(
				name=lib_name,
				type=ftype,
				layers=[self.Layer],
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
			L.warning(
				"Filesystem library change notifications are unavailable; inotify is not initialized.",
				struct_data={"base_path": self.BasePath, "path": path},
			)
			return
		self._subscribe_recursive(path, path)


	def _subscribe_recursive(self, subscribed_path, path_to_be_listed):
		binary = (self.BasePath + path_to_be_listed).encode()
		wd = inotify_add_watch(self.FD, binary, IN_ALL_EVENTS)
		if wd == -1:
			L.error(
				"Cannot watch library directory for changes; inotify_add_watch failed.",
				struct_data={"path": self.BasePath + path_to_be_listed, "layer": self.Layer},
			)
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

			self.AggrEvents.append((wd, mask, cookie, name))

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

				# Skip dotted dirs except internal ones ending with .io or .d
				if os.path.isdir(full_path) and '.' in entry and not entry.endswith(('.io', '.d')):
					continue

				self._recursive_find(full_path, filename, results)


class FileSystemLibraryProvider(SimpleFileSystemLibraryProvider):
	"""
	Filesystem provider with ZooKeeper-like target semantics.

	Targets differ only by filesystem root:

	- global:   <BasePath>
	- tenant:   <BasePath>/.tenants/<tenant>
	- personal: <BasePath>/.personal/<tenant>/<credentials>

	Library path `/foo` is always joined under that root. Missing target
	context (no tenant / credentials) skips that target; it never aliases
	another target.

	read(): personal → tenant → global
	list(): personal + tenant + global (no merging by name)

	subscribe(path, target):
		None / "global"        -> watch global path
		"tenant"               -> watch path under every tenant in /.tenants
		("tenant", "<tenant>") -> watch one tenant
		"personal"             -> watch current (tenant, credentials) scope
		("personal", "<cred>") -> watch one personal credential under current tenant
	"""

	# Precedence order for read/list overlays.
	Targets = ("personal", "tenant", "global")

	def __init__(self, library, path, layer, *, source, set_ready=True, enable_inotify=True):
		super().__init__(
			library, path, layer,
			source=source,
			set_ready=False,
			enable_inotify=enable_inotify,
		)

		self.DisabledFilePath = os.path.join(self.BasePath, '.disabled.yaml')

		if set_ready:
			self.App.TaskService.schedule(self._set_ready())


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


	def _target_base(
		self,
		target: typing.Optional[str],
		*,
		tenant_id: typing.Optional[str] = None,
		cred_id: typing.Optional[str] = None,
	) -> typing.Optional[str]:
		"""
		Return the absolute filesystem root for a target, or None if that
		target cannot be resolved with the given/current context.
		"""
		if target in (None, "global"):
			return self.BasePath

		if target == "tenant":
			if not tenant_id:
				return None
			return os.path.join(self.BasePath, ".tenants", tenant_id)

		if target == "personal":
			if not tenant_id or not cred_id:
				return None
			return os.path.join(self.BasePath, ".personal", tenant_id, cred_id)

		raise ValueError("Unexpected target: {!r}".format(target))


	def build_path(
		self,
		path: str,
		target: typing.Optional[str] = "global",
		*,
		tenant_id: typing.Optional[str] = None,
		cred_id: typing.Optional[str] = None,
	) -> typing.Optional[str]:
		"""
		Build an absolute filesystem path for `path` under the given target root.

		Returns:
			Absolute filesystem path, or None when the target cannot be resolved
			(missing tenant/credentials). Never falls back to another target.

		Raises:
			ValueError: path traversal outside the target root.
		"""
		assert path[:1] == '/'
		assert '//' not in path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"

		if target in ("tenant", "personal") and tenant_id is None:
			tenant_id = self._current_tenant_id()
		if target == "personal" and cred_id is None:
			cred_id = self._current_credentials_id()

		base = self._target_base(target, tenant_id=tenant_id, cred_id=cred_id)
		if base is None:
			return None

		base_norm = os.path.normpath(base)
		if path == '/':
			full = base_norm
		else:
			full = os.path.normpath(os.path.join(base_norm, path.lstrip('/')))

		if full != base_norm and not full.startswith(base_norm + os.sep):
			raise ValueError("Path traversal detected")

		return full


	async def read(self, path: str) -> typing.Optional[typing.IO]:
		"""
		Read a file from overlays in precedence order: personal → tenant → global.
		"""
		self._validate_read_path(path)

		for target in self.Targets:
			try:
				fs_path = self.build_path(path, target)
			except ValueError:
				continue
			if fs_path is None:
				continue
			if os.path.isfile(fs_path):
				return io.FileIO(fs_path, 'rb')

		return None


	async def list(self, path: str) -> list:
		"""
		List directory items from overlays: personal + tenant + global.
		Missing overlay roots contribute nothing (ZooKeeper semantics).
		"""
		items = []
		for target in self.Targets:
			try:
				node_path = self.build_path(path, target)
			except ValueError:
				continue
			if node_path is None:
				continue
			try:
				items.extend(self._list_from_node_path(node_path, path, target=target))
			except KeyError:
				# Overlay path does not exist → empty contribution
				pass

		return items


	def _list_from_node_path(self, node_path: str, base_path: str, target="global"):
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProvider.".format(base_path))

		items = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			try:
				fstat = os.stat(fname)
			except FileNotFoundError:
				continue

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

			if any(x.startswith('.') for x in lib_name.split('/')):
				continue

			if self.Layer == 0:
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


	def _iter_subscription_bases(self, target: typing.Union[str, tuple, None]):
		"""Yield absolute filesystem roots to watch for `target`."""
		if target in {None, "global"}:
			base = self._target_base("global")
			if base is not None:
				yield base
			return

		if target == "tenant":
			tenants_root = os.path.join(self.BasePath, ".tenants")
			if not os.path.isdir(tenants_root):
				return
			for name in sorted(os.listdir(tenants_root)):
				if name.startswith('.'):
					continue
				tenant_path = os.path.join(tenants_root, name)
				if os.path.isdir(tenant_path):
					yield tenant_path
			return

		if isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			base = self._target_base("tenant", tenant_id=target[1])
			if base is not None:
				yield base
			return

		if target == "personal":
			base = self._target_base(
				"personal",
				tenant_id=self._current_tenant_id(),
				cred_id=self._current_credentials_id(),
			)
			if base is not None:
				yield base
			return

		if isinstance(target, tuple) and len(target) == 2 and target[0] == "personal":
			base = self._target_base(
				"personal",
				tenant_id=self._current_tenant_id(),
				cred_id=target[1],
			)
			if base is not None:
				yield base
			return

		raise ValueError("Unexpected target: {!r}".format(target))


	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		if self.FD is None:
			L.warning(
				"Filesystem library change notifications are unavailable; inotify is not initialized.",
				struct_data={"base_path": self.BasePath, "path": path},
			)
			return

		for fs_root in self._iter_subscription_bases(target):
			if path == '/':
				node_path = os.path.normpath(fs_root)
			else:
				node_path = os.path.normpath(
					os.path.join(os.path.normpath(fs_root), path.lstrip('/'))
				)

			if not os.path.isdir(node_path):
				continue
			self._subscribe_recursive(path, path, fs_root)


	def _subscribe_recursive(self, subscribed_path, path_to_be_listed, fs_root=None):
		if fs_root is None:
			fs_root = self.BasePath

		if path_to_be_listed == '/':
			node_path = os.path.normpath(fs_root)
		else:
			node_path = os.path.normpath(
				os.path.join(os.path.normpath(fs_root), path_to_be_listed.lstrip('/'))
			)

		if not os.path.isdir(node_path):
			return

		wd = inotify_add_watch(self.FD, node_path.encode(), IN_ALL_EVENTS)
		if wd == -1:
			L.error(
				"Cannot watch library directory for changes; inotify_add_watch failed.",
				struct_data={"path": node_path, "layer": self.Layer},
			)
			return
		self.WDs[wd] = (subscribed_path, path_to_be_listed, fs_root)

		try:
			items = self._list_from_node_path(node_path, path_to_be_listed, target="global")
		except KeyError:
			return

		for item in items:
			if item.type == "dir":
				self._subscribe_recursive(subscribed_path, item.name, fs_root)


	def _on_inotify_read(self):
		data = os.read(self.FD, 64 * 1024)

		pos = 0
		while pos < len(data):
			wd, mask, cookie, namesize = struct.unpack_from(EVENT_FMT, data, pos)
			pos += EVENT_SIZE + namesize
			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			if mask & IN_ISDIR == IN_ISDIR and ((mask & IN_CREATE == IN_CREATE) or (mask & IN_MOVED_TO == IN_MOVED_TO)):
				subscribed_path, child_path, fs_root = self.WDs[wd]
				self._subscribe_recursive(subscribed_path, "/".join([child_path.rstrip("/"), name]), fs_root)

			if mask & IN_IGNORED == IN_IGNORED:
				del self.WDs[wd]
				continue

			watch = self.WDs.get(wd)
			if watch is not None:
				_, child_path, fs_root = watch
				if child_path == '/':
					watched_dir = os.path.normpath(fs_root)
				else:
					watched_dir = os.path.normpath(
						os.path.join(os.path.normpath(fs_root), child_path.lstrip('/'))
					)
				full_path = os.path.join(watched_dir, name) if name else watched_dir
				if os.path.normpath(full_path) == os.path.normpath(self.DisabledFilePath):
					self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

			self.AggrEvents.append((wd, mask, cookie, name))

		self.AggrTimer.restart(0.2)
