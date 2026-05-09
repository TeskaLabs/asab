import os
import asyncio

from .filesystem import FileSystemLibraryProvider


class CacheLibraryProvider(FileSystemLibraryProvider):

	def __init__(self, library, path, layer, *, repodir, ready_file):
		self.ReadyFile = ready_file
		super().__init__(library, repodir, layer, set_ready=False)

		self.App.TaskService.schedule(self.wait_for_ready())


	async def wait_for_ready(self):
		while not os.path.exists(self.ReadyFile):
			await asyncio.sleep(1)
		await self._set_ready()
