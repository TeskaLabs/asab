import asyncio
import typing


class Timer(object):
	"""
	The relative and optionally repeating timer for asyncio.

	This class is simple relative timer that generate an event after a given time,
	and optionally repeating in regular intervals after that.
	The timer object is initialized as stopped.

	Attributes:
		App (asab.Application): Reference to the ASAB application.
		Handler (asyncio.Coroutine | asyncio.Task): A coroutine or future that will be called when a timer triggers.
		Task (asyncio.Future | asyncio.Task | None): A future that represents the timer task.
		AutoRestart (bool): If `True` then a timer will be automatically restarted after triggering.

	Examples:
	```python
	class TimerApplication(asab.Application):
		async def initialize(self):
			self.Timer = asab.Timer(self, self.on_tick, autorestart=True)
			self.Timer.start(1) #(1)

		async def on_tick(self): #(2)
			print("Think!")
	```

	1. The timer will trigger a message publishing at every second.
	2. This function has to be a coroutine.

	!!! note
		The implementation idea was borrowed from [StackOverflow discussion](https://stackoverflow.com/questions/45419723/python-timer-with-asyncio-coroutine).
	"""

	def __init__(self, app, handler, autorestart=False):
		self.App = app
		self.Handler = handler
		self.Task = None
		self.AutoRestart = autorestart

		app.PubSub.subscribe("Application.stop!", self._on_stop)


	def start(self, timeout: typing.Union[int, float]):
		"""
		Start the `Timer` with new timeout.

		Args:
			timeout (int | float): A timer delay in seconds.

		Raises:
			RuntimeError: If the `Timer` has already started.
		"""
		if self.is_started():
			raise RuntimeError("Timer is already started")
		self.Task = asyncio.ensure_future(self._job(timeout))


	def stop(self):
		"""
		Stop the timer.
		"""
		if self.Task is not None:
			self.Task.cancel()
			self.Task = None


	def restart(self, timeout: typing.Union[int, float]):
		"""
		Restart the timer with a new timeout.

		Args:
			timeout (int | float): A new timeout in seconds.
		"""

		if self.is_started():
			self.stop()
		self.start(timeout)


	def is_started(self) -> bool:
		"""
		Check if the `Timer` has started.

		Returns:
			`True` if the `Timer` has started.
		"""
		return self.Task is not None


	async def _job(self, timeout):
		await asyncio.sleep(timeout)
		self.Task = None
		if self.AutoRestart:
			self.start(timeout)
		await self.Handler()


	def _on_stop(self, message_type, n):
		# This is to ensure timer stop on application exit
		self.stop()
