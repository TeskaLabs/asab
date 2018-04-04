Undocumented items:
	
	- 3x Ctrl-C leads to emergency exit
	- optional dependency on win32api when processing Ctrl-C on Windows (pip install pypiwin32)
	- Compatibility with pypy
	- Application.tick/10!, Application.tick/60! ... Also Publish-Subscribe event ``Application.tick!`` is published periodically during run-time, a tick period is configured by ``[general] tick_period``. The default period is one second.
	- -v mode (self.Loop.set_debug(True), ...)
	- -d -> daemonise (via python-daemon) + [general] 'pidfile', 'uid' and 'gid'

