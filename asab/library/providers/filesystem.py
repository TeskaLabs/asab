import io
import os
import stat
import glob
import typing
import functools
import logging
import ctypes
import struct

from .abc import LibraryProviderABC
from ..item import LibraryItem
from ...timer import Timer

#

L = logging.getLogger(__name__)

#

libc6 = ctypes.cdll.LoadLibrary('libc.so.6')


class FileSystemLibraryProvider(LibraryProviderABC):

	# inotify constants
	IN_ACCESS = 0x00000001  #: File was accessed
	IN_MODIFY = 0x00000002  #: File was modified
	IN_ATTRIB = 0x00000004  #: Metadata changed
	IN_CLOSE_WRITE = 0x00000008  #: Writable file was closed
	IN_CLOSE_NOWRITE = 0x00000010  #: Unwritable file closed
	IN_OPEN = 0x00000020  #: File was opened
	IN_MOVED_FROM = 0x00000040  #: File was moved from X
	IN_MOVED_TO = 0x00000080  #: File was moved to Y
	IN_CREATE = 0x00000100  #: Subfile was created
	IN_DELETE = 0x00000200  #: Subfile was deleted
	IN_DELETE_SELF = 0x00000400  #: Self was deleted
	IN_MOVE_SELF = 0x00000800  #: Self was moved

	IN_UNMOUNT = 0x00002000  #: Backing fs was unmounted
	IN_Q_OVERFLOW = 0x00004000  #: Event queue overflowed
	IN_IGNORED = 0x00008000  #: File was ignored

	IN_ONLYDIR = 0x01000000  #: only watch the path if it is a directory
	IN_DONT_FOLLOW = 0x02000000  #: don't follow a sym link
	IN_EXCL_UNLINK = 0x04000000  #: exclude events on unlinked objects
	IN_MASK_ADD = 0x20000000  #: add to the mask of an already existing watch
	IN_ISDIR = 0x40000000  #: event occurred against dir
	IN_ONESHOT = 0x80000000  #: only send event once

	IN_ALL_EVENTS = IN_MODIFY | IN_MOVED_FROM | IN_MOVED_TO | IN_CREATE | IN_DELETE | IN_DELETE_SELF | IN_MOVE_SELF | IN_Q_OVERFLOW

	# inotify function prototypes
	inotify_init = libc6.inotify_init
	inotify_init.argtypes = []
	inotify_init.restype = ctypes.c_int

	inotify_add_watch = libc6.inotify_add_watch
	inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
	inotify_add_watch.restype = ctypes.c_int


	_EVENT_FMT = 'iIII'
	_EVENT_SIZE = struct.calcsize(_EVENT_FMT)

	def __init__(self, library, path, *, set_ready=True):
		'''
		`set_ready` can be used to disable/defer `self._set_ready` call.
		'''

		super().__init__(library)
		self.BasePath = os.path.abspath(path)
		while self.BasePath.endswith("/"):
			self.BasePath = self.BasePath[:-1]

		L.info("is connected.", struct_data={'path': path})
		# Filesystem is always ready (or you have a serious problem)
		if set_ready:
			self.App.TaskService.schedule(self._set_ready())

		# Open inotify file descriptor
		self.fd = self.inotify_init()

		self.App.Loop.add_reader(self.fd, self._on_inotify_read)
		self.AggrTimer = Timer(self.App, self._on_aggr_timer)
		self.AggrEvents = []
		self.WDs = {}


	async def read(self, path: str) -> typing.IO:

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		try:
			return io.FileIO(node_path, 'rb')

		except FileNotFoundError:
			return None

		except IsADirectoryError:
			return None


	async def list(self, path: str) -> list:
		return self._list(path)

	def _list(self, path: str):

		assert path[:1] == '/'
		if path != '/':
			node_path = self.BasePath + path
		else:
			node_path = self.BasePath

		assert '//' not in node_path
		assert node_path[0] == '/'
		assert len(node_path) == 1 or node_path[-1:] != '/'

		iglobpath = os.path.join(node_path, "*")

		exists = os.access(node_path, os.R_OK) and os.path.isdir(node_path)
		if not exists:
			raise KeyError(" '{}' not found".format(path))

		items = []
		for fname in glob.iglob(iglobpath):

			fstat = os.stat(fname)

			assert fname.startswith(node_path)
			fname = fname[len(node_path) + 1:]

			if stat.S_ISREG(fstat.st_mode):
				ftype = "item"
			elif stat.S_ISDIR(fstat.st_mode):
				ftype = "dir"
			else:
				ftype = "?"

			# Remove any component that starts with '.'
			startswithdot = functools.reduce(lambda x, y: x or y.startswith('.'), fname.split(os.path.sep), False)
			if startswithdot:
				continue

			items.append(LibraryItem(
				name=(path + fname) if path == '/' else (path + '/' + fname),
				type=ftype,
				providers=[self],
			))

		return items


	def _on_inotify_read(self):
		data = os.read(self.fd, 64 * 1024)

		pos = 0
		while pos < len(data):
			wd, mask, cookie, namesize = struct.unpack_from(self._EVENT_FMT, data, pos)
			pos += self._EVENT_SIZE + namesize
			name = (data[pos - namesize: pos].split(b'\x00', 1)[0]).decode()

			if mask & self.IN_ISDIR == self.IN_ISDIR and mask & self.IN_CREATE == self.IN_CREATE:
				subscribed_path, child_path = self.WDs[wd]
				self._subscribe_recursive(subscribed_path, "/".join([child_path, name]))

			self.AggrEvents.append((wd, mask, cookie, os.fsdecode(name)))

		self.AggrTimer.restart(0.2)


	async def _on_aggr_timer(self):
		to_advertise = set()
		# TODO: race condition?: self.AggrEvents can be modified during this for cycle by _on_inotify_read() method
		# copy self.AggrEvents, clear self.AggrEvents and iterate through a copy?
		for wd, mask, cookie, name in self.AggrEvents:
			subscribed_path, _ = self.WDs.get(wd)
			to_advertise.add(subscribed_path)
		self.AggrEvents.clear()

		for path in to_advertise:
			self.App.PubSub.publish("ASABLibrary.change!", self, path)


	def subscribe(self, path):
		self._subscribe_recursive(path, path)

	def _subscribe_recursive(self, subscribed_path, path_to_be_listed):
		binary = (self.BasePath + path_to_be_listed).encode()
		wd = self.inotify_add_watch(self.fd, binary, self.IN_ALL_EVENTS)
		if wd == -1:
			# TODO: -1 means some error - what should happen then?
			return
		self.WDs[wd] = (subscribed_path, path_to_be_listed)

		for item in self._list(path_to_be_listed):
			if item.type == "dir":
				self._subscribe_recursive(subscribed_path, item.name)


	async def finalize(self, app):
		self.App.Loop.remove_reader(self.fd)
		os.close(self.fd)
