import asab
import concurrent.futures


class ProactorService(asab.Service):
	"""
	Proactor service is useful for running CPU bound operations from asynchronous part of the code that would potentially block the main thread.
	It allows to run these processes from different threads.
	"""

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Loop = app.Loop

		max_workers = asab.Config.get('asab:proactor', 'max_workers')
		try:
			max_workers = int(max_workers)
		except BaseException:
			max_workers = None
		if max_workers <= 0:
			max_workers = None

		self.Executor = concurrent.futures.ThreadPoolExecutor(
			max_workers=max_workers,  # The maximum number of threads that can be used to execute the given calls.
			# If None, ThreadPoolExecutor will determine the number itself based on number of CPU's.
			thread_name_prefix="AsabProactorThread"
		)

		if asab.Config.get('asab:proactor', 'default_executor'):
			self.Loop.set_default_executor(self.Executor)


	# There was the method run, which is obsolete
	def execute(self, func, *args):
		"""
		Execute `func(*args)` in the thread from the Proactor Service pool.
		Return Future or Task that must be awaited and it provides the result of the `func()` call.
		"""
		return self.Loop.run_in_executor(self.Executor, func, *args)


	def schedule(self, func, *args):
		"""
		Execute `func(*args)` in the thread from the Proactor Service pool.
		The result of the future is discarded (using Task Service).
		"""

		future = self.execute(func, *args)
		self.App.TaskService.schedule(future)


	def schedule_threadsafe(self, func, *args):
		"""
		Execute `func(*args)` in the thread from the Proactor Service pool.
		The result of the future is discarded (using Task Service).
		"""

		future = self.execute(func, *args)
		self.App.TaskService.schedule_threadsafe(future)
