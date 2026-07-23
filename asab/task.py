import logging
import asyncio
import typing

import asab

#

L = logging.getLogger(__name__)

#


class TaskService(asab.Service):
	"""
	Task service is for managed execution of fire-and-forget, one-off, background tasks.
	Task can be a coroutine, `asyncio.Future` or `asyncio.Task` and it is executed in the main event loop.

	The result of the task is collected (and discarded) automatically.
	When the task raises Exception, it will be printed to the log.
	"""

	def __init__(self, app, service_name="asab.TaskService"):
		super().__init__(app, service_name)

		self.NewTasks = asyncio.Queue()
		self.PendingTasks = set()
		self.Main = None


	async def initialize(self, app):
		self.start()


	def start(self):
		assert self.Main is None
		self.Main = asyncio.ensure_future(self.main())
		self.Main.add_done_callback(self._main_task_exited)


	async def finalize(self, app):
		if self.Main is not None:

			task = self.Main
			self.Main = None

			task.cancel()
			try:
				await task
			except asyncio.CancelledError:
				pass
			except Exception:
				L.exception("Background task failed during TaskService shutdown.")

		for task in list(self.PendingTasks):
			task.cancel()
			try:
				await task
				self.PendingTasks.remove(task)
			except asyncio.CancelledError:
				self.PendingTasks.remove(task)
			except Exception:
				L.exception("TaskService main loop failed during application shutdown.")


		total_tasks = len(self.PendingTasks) + self.NewTasks.qsize()
		if total_tasks > 0:
			L.warning(
				"TaskService stopped with background tasks that were not completed.",
				struct_data={
					"pending_tasks": len(self.PendingTasks),
					"queued_tasks": self.NewTasks.qsize(),
				},
			)


	def _main_task_exited(self, ctx):
		if self.Main is None:
			return
		try:
			self.Main.result()
		except asyncio.CancelledError:
			pass
		except Exception:
			L.exception("TaskService main loop failed unexpectedly.")

		self.Main = None
		L.warning(
			"TaskService main loop exited unexpectedly; restarting the task dispatcher.",
		)
		self.start()


	def _prepare_task(self, task):
		if task is None:
			L.warning(
				"Ignored scheduled background task because the task object is None.",
			)
			return None

		if isinstance(task, typing.Coroutine):
			return asyncio.create_task(task)

		if isinstance(task, (asyncio.Task, asyncio.Future)):
			return task

		L.warning(
			"Ignored scheduled background task because of an unsupported task type.",
			struct_data={"task_type": type(task).__name__},
		)
		return None


	def schedule(self, *tasks):
		"""
		Schedule a task (or tasks) for immediate fire-and-forget execution (e.g. compressing files).

		Examples:

		```python
		app.TaskService.schedule(self._start())
		```
		"""
		for task in tasks:
			self.NewTasks.put_nowait(task)


	def schedule_threadsafe(self, *tasks):
		"""
		Schedule a task (or tasks) threadsafe for immediate fire-and-forget execution (e.g. compressing files).
		Use this method to schedule task from a thread to be executed in the main thread.

		Examples:

		```python
		app.TaskService.schedule_threadsafe(self._start())
		```
		"""
		for task in tasks:
			self.App.Loop.call_soon_threadsafe(self.NewTasks.put_nowait, task)


	def run_forever(self, *async_functions):
		"""
		Schedule an async function (or functions) for immediate fire-and-forget execution.
		The function is expected to run forever.
		If function exits, the error is logged and the function is restarted.
		Function is called without any argument.

		Examples:

		```python
		class MyClass(object):
			def __init__(self, app):
				...
				app.TaskService.run_forever(self.my_forever_method)

			async def my_forever_method(self):
				while True:
					await ...
		```
		"""
		for async_fn in async_functions:
			self.NewTasks.put_nowait(
				forever(async_fn)
			)


	async def main(self):
		while True:

			while self.NewTasks.qsize() > 0:
				task = self._prepare_task(self.NewTasks.get_nowait())
				if task is not None:
					self.PendingTasks.add(task)

			if len(self.PendingTasks) == 0:
				# Block until a new task is scheduled
				task = self._prepare_task(await self.NewTasks.get())
				if task is not None:
					self.PendingTasks.add(task)

			else:
				done, self.PendingTasks = await asyncio.wait(self.PendingTasks, timeout=1.0)
				for task in done:
					try:
						await task
					except Exception:
						task_name = task.get_name() if hasattr(task, "get_name") else repr(task)
						try:
							exc = task.exception()
							L.exception(
								"Scheduled background task failed.",
								exc_info=exc,
								struct_data={"task": task_name},
							)
						except Exception:
							L.exception(
								"Scheduled background task failed; stack trace is not available.",
								struct_data={"task": task_name},
							)
					self.App.PubSub.publish("TaskService.task_done!", task)


async def forever(async_fn):
	while True:
		try:
			await async_fn()
		except asyncio.CancelledError:
			break
		except Exception:
			L.exception(
				"Long-running background task exited with an error; it will be restarted on the next iteration.",
				struct_data={"callable": getattr(async_fn, "__qualname__", repr(async_fn))},
			)
