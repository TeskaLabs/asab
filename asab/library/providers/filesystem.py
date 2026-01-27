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
		# Check for `file://` prefix and strip it if present
		if path.startswith('file://'):
			path = path[7:]   # Strip "file://"

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

	def _personal_path(self, path: str, tenant_id, cred_id):
		assert path[:1] == '/'
		if not tenant_id or not cred_id:
			return None
		return (self.BasePath + '/.personal/{}/{}{}'.format(tenant_id, cred_id, path)).rstrip("/")

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
			return (self.BasePath + "/.personal/{}/{}{}".format(tenant_id, cred_id, path)).rstrip("/")

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
			personal_node = (self.BasePath + '/.personal/{}/{}{}'.format(tenant_id, cred_id, path))
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

	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		if self.FD is None:
			L.warning(
				"Cannot subscribe to changes in the filesystem layer of the library: '{}'".format(
					self.BasePath
				)
			)
			return

		# ---- GLOBAL ----
		if target is None or target == "global":
			actual = self.build_path(path)
			if os.path.isdir(actual):
				self._subscribe_recursive(
					subscribed_path=path,
					path_to_be_listed=path,
					scope="global",
				)

		# ---- TENANT (all) ----
		elif target == "tenant":
			for tenant in await self._get_tenants():
				actual = self.build_path(path, tenant_specific=True, tenant=tenant)
				if os.path.isdir(actual):
					self._subscribe_recursive(
						subscribed_path=path,
						path_to_be_listed=path,
						scope="tenant",
						tenant_id=tenant,
					)

		# ---- TENANT (one) ----
		elif isinstance(target, tuple) and target[0] == "tenant":
			tenant = target[1]
			actual = self.build_path(path, tenant_specific=True, tenant=tenant)
			if os.path.isdir(actual):
				self._subscribe_recursive(
					subscribed_path=path,
					path_to_be_listed=path,
					scope="tenant",
					tenant_id=tenant,
				)

		# ---- PERSONAL (all credentials) ----
		elif target == "personal":
			for tenant_id, cred_id in await self._get_personal_scopes():
				actual = (self.BasePath + "/.personal/{}/{}{}".format(tenant_id, cred_id, path))
				if os.path.isdir(actual):
					self._subscribe_recursive(
						subscribed_path=path,
						path_to_be_listed=path,
						scope="personal",
						tenant_id=tenant_id,
						cred_id=cred_id,
					)

		# ---- PERSONAL (one credential) ----
		elif isinstance(target, tuple) and target[0] == "personal":
			cred_id = target[1]
			for tenant_id in await self._get_tenants():
				actual = (self.BasePath + "/.personal/{}/{}{}".format(tenant_id, cred_id, path))
				if os.path.isdir(actual):
					self._subscribe_recursive(
						subscribed_path=path,
						path_to_be_listed=path,
						scope="personal",
						tenant_id=tenant_id,
						cred_id=cred_id,
					)

		else:
			raise ValueError("Unexpected target: {!r}".format(target))

	def _subscribe_recursive(
		self,
		subscribed_path,
		path_to_be_listed,
		*,
		scope="global",
		tenant_id=None,
		cred_id=None,
	):
		if scope == "global":
			fs_dir = self.build_path(path_to_be_listed)

		elif scope == "tenant":
			fs_dir = self.build_path(
				path_to_be_listed,
				tenant_specific=True,
				tenant=tenant_id,
			)

		elif scope == "personal":
			fs_dir = (self.BasePath + "/.personal/{}/{}{}".format(tenant_id, cred_id, path_to_be_listed)).rstrip("/")

		else:
			return

		if not os.path.isdir(fs_dir):
			return

		wd = inotify_add_watch(self.FD, fs_dir.encode(), IN_ALL_EVENTS)
		if wd == -1:
			L.error("Error in inotify_add_watch")
			return

		self.WDs[wd] = {
			"subscribed_path": subscribed_path,
			"path": path_to_be_listed,
			"scope": scope,
			"tenant_id": tenant_id,
			"cred_id": cred_id,
		}

		# recurse
		try:
			items = self._list_subdirs_only(
				path_to_be_listed,
				scope=scope,
				tenant_id=tenant_id,
				cred_id=cred_id,
			)
		except KeyError:
			return

		for item in items:
			self._subscribe_recursive(
				subscribed_path,
				item,
				scope=scope,
				tenant_id=tenant_id,
				cred_id=cred_id,
			)

	def _list_subdirs_only(self, path, *, scope, tenant_id=None, cred_id=None):
		if scope == "global":
			node_path = self.build_path(path)

		elif scope == "tenant":
			node_path = self.build_path(
				path,
				tenant_specific=True,
				tenant=tenant_id,
			)

		elif scope == "personal":
			node_path = (self.BasePath + "/.personal/{}/{}{}".format(tenant_id, cred_id, path))

		else:
			raise KeyError(path)

		if not os.path.isdir(node_path):
			raise KeyError(path)

		subdirs = []
		for fname in glob.iglob(os.path.join(node_path, "*")):
			if os.path.isdir(fname):
				name = os.path.basename(fname)
				if not name.startswith("."):
					subdirs.append("{}/{}/".format(path.rstrip("/"), name))
		return subdirs

	def _on_inotify_read(self):
		data = os.read(self.FD, 64 * 1024)

		pos = 0
		while pos < len(data):
			wd, mask, cookie, namesize = struct.unpack_from(EVENT_FMT, data, pos)
			pos += EVENT_SIZE + namesize
			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			self.AggrEvents.append((wd, mask, cookie, name))

			info = self.WDs.get(wd)
			if not info:
				continue

			subscribed_path = info["subscribed_path"]
			child_path = info["path"]
			scope = info["scope"]
			tenant_id = info["tenant_id"]
			cred_id = info["cred_id"]

			if (mask & IN_ISDIR) and (mask & (IN_CREATE | IN_MOVED_TO)):
				self._subscribe_recursive(
					subscribed_path,
					"{}/{}/".format(child_path.rstrip("/"), name),
					scope=scope,
					tenant_id=tenant_id,
					cred_id=cred_id,
				)

			if mask & IN_IGNORED:
				del self.WDs[wd]
				continue

			# resolve actual filesystem path correctly
			fs_parent = self._resolve_fs_path_from_info(info)
			full_path = os.path.join(fs_parent, name)

			if os.path.normpath(full_path) == os.path.normpath(self.DisabledFilePath):
				self.App.TaskService.schedule(self.Library._read_disabled(publish_changes=True))

		self.AggrTimer.restart(0.2)

	async def _on_aggr_timer(self):
		to_advertise = set()

		for wd, mask, cookie, name in self.AggrEvents:
			info = self.WDs.get(wd)
			if not info:
				continue

			to_advertise.add(info["subscribed_path"])

		self.AggrEvents.clear()

		for path in to_advertise:
			if path is None:
				continue
			self.App.PubSub.publish("Library.change!", self, path)

	async def _get_tenants(self) -> typing.List[str]:
		tenants_dir = os.path.join(self.BasePath, ".tenants")
		if not os.path.isdir(tenants_dir):
			return []

		return [
			name for name in os.listdir(tenants_dir)
			if not name.startswith(".") and os.path.isdir(os.path.join(tenants_dir, name))
		]

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
