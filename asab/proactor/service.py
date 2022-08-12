import asab
import concurrent.futures


class ProactorService(asab.Service):

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
			max_workers=max_workers,
			thread_name_prefix="AsabProactorThread"
		)

		if asab.Config.get('asab:proactor', 'default_executor'):
			self.Loop.set_default_executor(self.Executor)


	# There was the method run, which is obsolete
	def execute(self, func, *args):
		'''
		The `execute` method executes func(*args) in the thread from the Proactor Service pool.
		The method returns the future/task that MUST BE awaited and it provides the result of the func() call.
		'''
		return self.Loop.run_in_executor(self.Executor, func, *args)


	def schedule(self, func, *args):
		'''
		The `schedule` method executes func(*args) in the thread from the Proactor Service pool.
		The result of the future is discarted (using Task Service)
		'''

		future = self.execute(func, *args)
		self.App.TaskService.schedule(future)
