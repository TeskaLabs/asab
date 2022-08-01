import logging
import asyncio

import asab

#

L = logging.getLogger(__name__)

#


class TaskService(asab.Service):

	'''
	Task service is for managed execution of fire-and-forget, one-off, background tasks.
	The task is a coroutine, future (asyncio.ensure_future) or task (asyncio.create_task).
	The task is executed in the main event loop.
	The task should be a relatively short-lived (~5 seconds) asynchronous procedure.

	The result of the task is collected (and discarted) automatically
	and if there was an exception, it will be printed to the log.
	'''

	def __init__(self, app, service_name="asab.TaskService"):
		super().__init__(app, service_name)

		self.NewTasks = []
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
			except Exception as e:
				L.exception("Error '{}' during task service:".format(e))

		total_tasks = len(self.PendingTasks) + len(self.NewTasks)
		if total_tasks > 0:
			L.warning("{} pending and incompleted tasks".format(total_tasks))


	def _main_task_exited(self, ctx):
		if self.Main is None:
			return
		try:
			self.Main.result()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			L.exception("Error '{}' during task service:".format(e))

		self.Main = None
		L.warning("Main task exited unexpectedly, restarting ...")
		self.start()


	def schedule(self, *tasks):
		'''
		Schedule execution of task(s).
		Tasks will be started in 1-5 seconds (not immediately).

		Task can be a simple coroutine, future or task.
		'''
		self.NewTasks.extend(tasks)


	async def main(self):
		while True:

			while len(self.NewTasks) > 0:
				task = self.NewTasks.pop()
				self.PendingTasks.add(task)

			if len(self.PendingTasks) == 0:
				await asyncio.sleep(5.0)
			else:
				done, self.PendingTasks = await asyncio.wait(self.PendingTasks, timeout=1.0)
				for task in done:
					try:
						await task
					except Exception as e:
						L.exception("Error '{}' during task:".format(e))
