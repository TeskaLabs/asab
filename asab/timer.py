import asyncio


class Timer(object):
	'''
	T.__init__(callback, autorestart=False, loop=None) -> Timer.

	The relative and optionally repeating timer for asyncio.

	This class is simple relative timer that generate an event after a given time, and optionally repeating in regular intervals after that.

	:param callback: A coro or future that will be called when a timer triggers.
	:param boolean autorestart: If `True` then a timer will be automatically restarted after triggering.
	:param loop: An event loop, if not specificed, the default event loop is used.

	:ivar Callback: A coro or future that will be called when a timer triggers.
	:ivar Task: A future that represent the timer task.
	:ivar Loop: An event loop.
	:ivar boolean AutoRestart: If `True` then a timer will be automatically restarted after triggering.

	The timer object is initialized as stopped.

	*Note*: The implementation idea is borrowed from "`Python - Timer with asyncio/coroutine <https://stackoverflow.com/questions/45419723/python-timer-with-asyncio-coroutine>`_" question on StackOverflow.
	'''

	def __init__(self, callback, autorestart=False, loop=None):
		self.Callback = callback
		self.Task = None
		self.Loop = loop
		self.AutoRestart = autorestart


	def start(self, timeout):
		'''
		Start the timer.

		:param float/int timeout: A timer delay in seconds.
		'''

		if self.is_started():
			raise RuntimeError("Timer is already started")
		self.Task = asyncio.ensure_future(self._job(timeout), loop=self.Loop)


	def stop(self):
		'''
		Stop the timer.
		'''


		if self.Task is not None:
			self.Task.cancel()
			self.Task = None


	def restart(self, timeout):
		'''
		Restart the timer.

		:param float/int timeout: A timer delay in seconds.
		'''

		if self.is_started():
			self.stop()
		self.start(timeout)


	def is_started(self):
		'''
		T.is_started() -> boolean
		Return `True` is the timer is started otherwise returns `False`.
		'''
		return self.Task is not None


	async def _job(self, timeout):
		await asyncio.sleep(timeout)
		self.Task = None
		if self.AutoRestart:
			self.start(timeout)
		await self.Callback()
