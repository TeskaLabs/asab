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
from ...contextvars import Tenant

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


class FileSystemLibraryProviderTarget(LibraryProviderABC):
	"""
	Filesystem provider with ZooKeeper-like target semantics:

	- global path: <BasePath>/<path>
	- tenant path: <BasePath>/.tenants/<tenant>/<path>

	read():
		tenant → global

	list():
		tenant-items + global-items (no merging by name)

	subscribe(path, target):
		None/"global" -> watch global path
		"tenant" -> watch in all tenants under /.tenants
		("tenant", "<tenant>") -> watch in one tenant
	"""

	def __init__(self, library, path, layer, *, set_ready=True):
		super().__init__(library, layer)

		if path.startswith('file://'):
			path = path[7:]

		path = os.path.abspath(path)
		self.BasePath = path.rstrip("/")

		L.info("is connected.", struct_data={'path': path})
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())

		if inotify_init is not None:
			init = inotify_init()
			if init == -1:
				L.warning("Subscribing to library changes in filesystem provider is not available. Inotify was not initialized.")
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


	def build_path(self, path, tenant_specific=False, tenant=None):
		assert path[:1] == '/'

		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		if tenant_specific:
			if tenant is None:
				try:
					tenant = Tenant.get()
				except LookupError:
					tenant = None

			if tenant:
				node_path = self.BasePath + '/.tenants/' + tenant + path

		node_path = node_path.rstrip("/")

		assert '//' not in node_path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"
		assert node_path[0] == '/', "Directory path must start with a forward slash (/). For example: /library/Templates/"

		return node_path


	async def read(self, path: str) -> typing.Optional[typing.IO]:
		# Tenant first
		try:
			tenant_node_path = self.build_path(path, tenant_specific=True)
			if os.path.isfile(tenant_node_path):
				return io.FileIO(tenant_node_path, 'rb')
		except Exception:
			# keep behavior similar to zk: just fall back
			pass

		# Global fallback
		node_path = self.build_path(path, tenant_specific=False)
		try:
			return io.FileIO(node_path, 'rb')
		except (FileNotFoundError, IsADirectoryError):
			return None


	async def list(self, path: str) -> list:
		# Global
		global_node_path = self.build_path(path, tenant_specific=False)
		global_items = self._list_from_node_path(global_node_path, path, target="global")

		# Tenant
		tenant_node_path = self.build_path(path, tenant_specific=True)
		if tenant_node_path != global_node_path:
			tenant_items = self._list_from_node_path(tenant_node_path, path, target="tenant")
		else:
			tenant_items = []

		return tenant_items + global_items


	def _list_from_node_path(self, node_path: str, base_path: str, target="global"):
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProviderTarget.".format(base_path))

		items = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			fstat = os.stat(fname)

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
				layer_label = "0:global" if target == "global" else "0:tenant"
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


	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		"""
		Match ZooKeeper provider semantics:

		target is None / "global"  -> watch global directory
		target == "tenant"         -> watch the directory in all tenants that exist
		target == ("tenant", t)    -> watch the directory only in tenant t
		"""
		if self.FD is None:
			L.warning("Cannot subscribe to changes in the filesystem layer of the library: '{}'".format(self.BasePath))
			return

		if target is None or target == "global":
			actual_dir = self.build_path(path, tenant_specific=False)
			if os.path.isdir(actual_dir):
				self._subscribe_recursive(path, path, tenant=None)

		elif target == "tenant":
			for tenant in await self._get_tenants():
				actual_dir = self.build_path(path, tenant_specific=True, tenant=tenant)
				if os.path.isdir(actual_dir):
					self._subscribe_recursive(path, path, tenant=tenant)

		elif isinstance(target, tuple) and len(target) == 2 and target[0] == "tenant":
			tenant = target[1]
			actual_dir = self.build_path(path, tenant_specific=True, tenant=tenant)
			if os.path.isdir(actual_dir):
				self._subscribe_recursive(path, path, tenant=tenant)

		else:
			raise ValueError("Unexpected target: {!r}".format(target))


	def _subscribe_recursive(self, subscribed_path, path_to_be_listed, tenant=None):
		# Watch one directory tree, either global or tenant-scoped.
		fs_dir = self.build_path(path_to_be_listed, tenant_specific=(tenant is not None), tenant=tenant)
		if not os.path.isdir(fs_dir):
			return

		binary = fs_dir.encode()
		wd = inotify_add_watch(self.FD, binary, IN_ALL_EVENTS)
		if wd == -1:
			L.error("Error in inotify_add_watch")
			return

		# Store the "subscription key" as library path + tenant for correct change publish behavior.
		child_key = path_to_be_listed
		if tenant is not None:
			# internal key includes tenant namespace like ZooKeeper implementation
			child_key = "/.tenants/{}{}".format(tenant, path_to_be_listed)

		self.WDs[wd] = (subscribed_path, child_key)

		# Recursively watch subdirs
		try:
			items = self._list_subdirs_only(path_to_be_listed, tenant=tenant)
		except KeyError:
			return

		for item in items:
			self._subscribe_recursive(subscribed_path, item, tenant=tenant)


	def _list_subdirs_only(self, path: str, tenant=None):
		node_path = self.build_path(path, tenant_specific=(tenant is not None), tenant=tenant)
		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError("Path '{}' not found by FileSystemLibraryProviderTarget.".format(path))

		subdirs = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			if not os.path.isdir(fname):
				continue
			rel_name = os.path.basename(fname)
			if rel_name.startswith('.'):
				continue
			subdirs.append("{}/{}/".format(path.rstrip("/"), rel_name))
		return subdirs


	def _on_inotify_read(self):
		data = os.read(self.FD, 64 * 1024)

		pos = 0
		while pos < len(data):
			wd, mask, cookie, namesize = struct.unpack_from(EVENT_FMT, data, pos)
			pos += EVENT_SIZE + namesize
			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			# Record events for aggregation (so _on_aggr_timer can publish changes)
			self.AggrEvents.append((wd, mask, cookie, name))

			if mask & IN_ISDIR == IN_ISDIR and ((mask & IN_CREATE == IN_CREATE) or (mask & IN_MOVED_TO == IN_MOVED_TO)):
				subscribed_path, child_path = self.WDs[wd]
				self._subscribe_recursive(subscribed_path, "/".join([child_path, name]))

			if mask & IN_IGNORED == IN_IGNORED:
				# cleanup
				del self.WDs[wd]
				continue

			full_path = os.path.join(self.BasePath, name)
			if os.path.normpath(full_path) == os.path.normpath(self.DisabledFilePath):
				self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

		self.AggrTimer.restart(0.2)

	async def _on_aggr_timer(self):
		to_advertise = set()

		for wd, mask, cookie, name in self.AggrEvents:
			subscribed_path, _ = self.WDs.get(wd, (None, None))
			to_advertise.add(subscribed_path)

		self.AggrEvents.clear()

		for path in to_advertise:
			if path is None:
				continue
			self.App.PubSub.publish("Library.change!", self, path)


	async def _get_tenants(self) -> typing.List[str]:
		tenants_dir = os.path.join(self.BasePath, ".tenants")
		if not os.path.isdir(tenants_dir):
			return []

		tenants = []
		for name in os.listdir(tenants_dir):
			if name.startswith('.'):
				continue
			full = os.path.join(tenants_dir, name)
			if os.path.isdir(full):
				tenants.append(name)

		return tenants


	async def find(self, filename: str) -> list:
		results = []
		self._recursive_find(self.BasePath, filename, results)
		return results


	def _recursive_find(self, path, filename, results):
		if not os.path.exists(path):
			return

		if os.path.isfile(path) and path.endswith(filename):
			item = LibraryItem(
				name=path[len(self.BasePath):],
				type="item",
				layers=[self.Layer],
				providers=[self],
			)
			results.append(item)
			return

		if os.path.isdir(path):
			for entry in os.listdir(path):
				full_path = os.path.join(path, entry)
				self._recursive_find(full_path, filename, results)


	async def finalize(self, app):
		if self.FD is not None:
			self.App.Loop.remove_reader(self.FD)
			os.close(self.FD)
