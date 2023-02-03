import ctypes
import struct

libc6 = ctypes.cdll.LoadLibrary('libc.so.6')

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
