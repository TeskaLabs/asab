import asyncio


class Timer(object):
	'''
	The timer for asyncio
	From https://stackoverflow.com/questions/45419723/python-timer-with-asyncio-coroutine
	'''

	def __init__(self, callback, autorestart=False, loop=None):
		self.Callback = callback
		self.Task = None
		self.Loop = loop
		self.AutoRestart = autorestart


	def is_started(self):
		return self.Task is not None


	def start(self, timeout):
		if self.is_started():
			raise RuntimeError("Timer is already started")
		self.Task = asyncio.ensure_future(self._job(timeout), loop=self.Loop)


	def stop(self):
		if self.Task is not None:
			self.Task.cancel()
			self.Task = None


	def restart(self, timeout):
		if self.is_started():
			self.stop()
		self.start(timeout)


	async def _job(self, timeout):
		await asyncio.sleep(timeout)
		self.Task = None
		if self.AutoRestart:
			self.start(timeout)
		await self.Callback()
