import asab
import concurrent.futures


class ProactorService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Loop = app.Loop
		
		max_workers = asab.Config.get('asab:proactor', 'max_workers')
		try:
			max_workers = int(max_workers)
		except:
			max_workers = None
		if max_workers <= 0: max_workers = None

		self.Executor = concurrent.futures.ThreadPoolExecutor(
			max_workers=max_workers,
			thread_name_prefix="AsabProactorThread"
		)

		if asab.Config.get('asab:proactor', 'default_executor'):
			self.Loop.set_default_executor(self.Executor)


	async def run(self, func, *args):
		return await self.Loop.run_in_executor(self.Executor, func, *args)
