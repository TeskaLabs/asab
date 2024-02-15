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

try:
	from .filesystem_inotify import inotify_init, inotify_add_watch, IN_CREATE, IN_ISDIR, IN_ALL_EVENTS, EVENT_FMT, EVENT_SIZE, IN_MOVED_TO, IN_IGNORED
except OSError:
	inotify_init = None

#

L = logging.getLogger(__name__)

#


class FileSystemLibraryProvider(LibraryProviderABC):

	def __init__(self, library, path, layer, *, set_ready=True):
		'''
		`set_ready` can be used to disable/defer `self._set_ready` call.
		'''

		super().__init__(library, layer)
		self.BasePath = os.path.abspath(path)
		while self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]

		L.info("is connected.", struct_data={'path': path})
		# Filesystem is always ready (or you have a serious problem)
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())

		# Open inotify file descriptor
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

		self.AggrEvents = []
		self.WDs = {}


	async def read(self, path: str, tenant: str) -> typing.IO:

		node_path = self.BasePath + path

		# Handling tenant
		if tenant not in [None, ""]:
			node_path = self.BasePath + "/.tenants/" + tenant + path

		# File path must start with '/'
		assert node_path[:1] == '/', "File path must start with a forward slash (/). For example: /library/Templates/file.json"
		# File path must end with the extension
		assert len(os.path.splitext(node_path)[1]) > 0, "File path must end with an extension. For example: /library/Templates/item.json"
		# File cannot contain '//'
		assert '//' not in node_path, "File path cannot contain double slashes (//). Example format: /library/Templates/item.json"

		try:
			return io.FileIO(node_path, 'rb')

		except FileNotFoundError:
			return None

		except IsADirectoryError:
			return None


	async def list(self, path: str, tenat: str) -> list:
		# This list method is completely synchronous, but it should look like asynchronous to make all list methods unified among providers.
		return self._list(path)


	def _list(self, path: str, tenant: str):

		node_path = self.BasePath + path
		# Handling tenant
		if tenant not in [None, ""]:
			node_path = self.BasePath + "/.tenants/" + tenant + path

		# Directory path must start with '/'
		assert node_path[:1] == '/', "Directory path must start with a forward slash (/). For example: /library/Templates/"
		# Directory path must end with '/'
		assert node_path[-1:] == '/', "Directory path must end with a forward slash (/). For example: /library/Templates/"
		# Directory cannot contain '//'
		assert '//' not in node_path, "Directory path cannot contain double slashes (//). Example format: /library/Templates/"

		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError(" '{}' not found".format(path))

		items = []
		for fname in glob.iglob(os.path.join(node_path, "*")):

			fstat = os.stat(fname)

			assert fname.startswith(self.BasePath)
			fname = fname[len(self.BasePath):]

			if stat.S_ISREG(fstat.st_mode):
				ftype = "item"
			elif stat.S_ISDIR(fstat.st_mode):
				ftype = "dir"
				fname += '/'
			else:
				ftype = "?"

			# Remove any component that starts with '.'
			if any(x.startswith('.') for x in fname.split('/')):
				continue

			items.append(LibraryItem(
				name=fname,
				type=ftype,
				layer=self.Layer,
				providers=[self],
			))

		return items

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
				layer=self.Layer,
				providers=[self],
			)
			results.append(item)
			return

		if os.path.isdir(path):
			for entry in os.listdir(path):
				full_path = os.path.join(path, entry)
				self._recursive_find(full_path, filename, results)


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

			self.AggrEvents.append((wd, mask, cookie, os.fsdecode(name)))

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


	async def subscribe(self, path):
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


	def tenant_exists(self, tenant: str) -> bool:
		"""
		Check if a tenant exists in the Zookeeper data store.

		This method verifies the existence of a tenant by checking its presence in the Zookeeper data store.
		It constructs the path to the tenant's data and queries Zookeeper to determine if the node exists.

		Parameters:
		tenant (str): The identifier of the tenant to check.

		Returns:
		bool: True if the tenant exists in the Zookeeper data store, False otherwise.
		"""
		if tenant in [None, ""]:
			return False

		tenant_path = self.BasePath + "/.tenants/" + tenant
		return os.path.exists(tenant_path)

	async def finalize(self, app):
		if self.FD is not None:
			self.App.Loop.remove_reader(self.FD)
			os.close(self.FD)
