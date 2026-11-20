import os
import logging
import asyncio

from .filesystem import SimpleFileSystemLibraryProvider

L = logging.getLogger(__name__)


class CacheLibraryProvider(SimpleFileSystemLibraryProvider):

	def __init__(self, library, path, layer, *, source, repodir, ready_file):
		self.ReadyFile = ready_file
		self.ContentDir = repodir
		super().__init__(library, repodir, layer, source=source, set_ready=False)

		self.ProviderKind = path.split("+", 1)[0] if "+" in path else "unknown"

		L.info(
			"Using cache library provider instead of downloading library content. For standalone or local development, remove cache_dir from configuration so the library downloads directly.",
			struct_data={
				"content_dir": self.ContentDir,
				"layer": self.Layer,
				"provider_kind": self.ProviderKind,
			},
		)

		# Wait for the ready file to be created by an external cache filler (typically ASAB Governator).
		self.App.TaskService.schedule(self.wait_for_ready())

	async def wait_for_ready(self):
		struct_data = {
			"content_dir": self.ContentDir,
			"layer": self.Layer,
			"provider_kind": self.ProviderKind,
		}

		cnt = 0
		while not os.path.exists(self.ReadyFile):
			if cnt >= 60 and cnt % 60 == 0:
				if os.path.isdir(self.ContentDir):
					L.error(
						"Cached library is not ready: the ready marker file is missing, "
						"but the cache content directory already exists. "
						"The cache filler is probably still populating the library; "
						"waiting may be enough. Check ASAB Governator or other cache-filler logs if this persists.",
						struct_data=struct_data,
					)
				else:
					L.error(
						"Cached library is not ready: the ready marker file and cache content directory are missing. "
						"This provider does not download library content; an external service "
						"(typically ASAB Governator) must populate the cache with a matching cache_dir and library provider. "
						"For standalone or local development, remove cache_dir from configuration so the library downloads directly.",
						struct_data=struct_data,
					)
			elif cnt >= 30 and cnt % 10 == 0:
				L.warning(
					"Waiting for cached library content to become ready.",
					struct_data=struct_data,
				)
			await asyncio.sleep(1)
			cnt += 1

		await self._set_ready()