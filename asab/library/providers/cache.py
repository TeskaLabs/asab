import os
import logging
import hashlib

from asab.config import Config
from asab.library.providers.filesystem import FileSystemLibraryProvider

L = logging.getLogger(__name__)


class CacheLibraryProvider(FileSystemLibraryProvider):
	"""
	A read-only cache wrapper that points at
	[library:cache].dir/@global/<layer_hash>.

	Any call to read()/list()/find()/subscribe() will serve from cache if present,
	or raise KeyError if the cache is missing to trigger fallback.
	"""

	def __init__(self, library, uri, layer):
		# 1) Compute the exact same layer_hash your LibraryCacheService wrote
		master_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()

		# 2) Locate the symlink under @global
		cache_root = Config.get("library:cache", "dir", fallback=None)
		if not cache_root:
			raise RuntimeError("Missing [library:cache].dir configuration")
		global_link = os.path.join(cache_root, "@global", master_hash)

		# 3) Remember for _cache_live()
		self.layer_hash = master_hash
		self.cache_dir = global_link

		# 4) Sanity-check cache_root exists
		if not os.path.isdir(cache_root):
			L.critical("Cache root '{}' not found, exiting.".format(cache_root))
			raise SystemExit(1)

		# 5) Warn if no snapshot directory is present yet
		if not self._cache_live():
			L.warning(
				"No cache snapshot for URI '{}' at '{}'.".format(uri, self.cache_dir)
			)

		# 6) Delegate to FileSystemLibraryProvider
		cache_uri = "file://{}".format(self.cache_dir.rstrip("/"))
		super().__init__(library, cache_uri, layer, set_ready=False)
		library.App.TaskService.schedule(self._set_ready(self._cache_live()))
		library.App.PubSub.subscribe("library.cache.ready!", self._on_cache_ready)
		library.App.PubSub.subscribe("library.cache.not_ready!", self._on_cache_not_ready)


	async def _on_cache_ready(self, *args):
		live = self._cache_live()
		if live and not self.IsReady:
			await self._set_ready(True)

	async def _on_cache_not_ready(self, *args):
		live = self._cache_live()
		if (not live) and self.IsReady:
			await self._set_ready(False)

	def _cache_live(self):
		if os.path.islink(self.cache_dir):
			return os.path.isdir(os.path.realpath(self.cache_dir))
		return os.path.isdir(self.cache_dir)

	async def read(self, path):
		if not self._cache_live():
			raise KeyError("No cache for '{}'".format(path))
		return await super().read(path)

	async def list(self, path):
		if not self._cache_live():
			raise KeyError("No cache for '{}'".format(path))
		return await super().list(path)

	async def find(self, path):
		if not self._cache_live():
			raise KeyError("No cache for '{}'".format(path))
		return await super().find(path)

	async def subscribe(self, path, target=None):
		if not self._cache_live():
			raise KeyError("No cache for '{}'".format(path))
		return await super().subscribe(path, target)
