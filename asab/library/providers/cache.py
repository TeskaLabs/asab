import os
import logging
import asyncio

from .filesystem import SimpleFileSystemLibraryProvider

L = logging.getLogger(__name__)


class CacheLibraryProvider(SimpleFileSystemLibraryProvider):

	def __init__(self, library, path, layer, *, repodir, ready_file):
		self.ReadyFile = ready_file
		super().__init__(library, repodir, layer, set_ready=False)

		# Wait for the ready file to be created by the asab-library service, indicating that the cache folder is ready.
		self.App.TaskService.schedule(self.wait_for_ready())


	async def wait_for_ready(self):
		cnt = 0
		while not os.path.exists(self.ReadyFile):
			if cnt > 20 and cnt % 10 == 0:
				L.warning("Waiting for the cache to be ready...", struct_data={'path': self.ReadyFile})
			await asyncio.sleep(1)
			cnt += 1
		await self._set_ready()
