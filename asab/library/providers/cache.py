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

		# 3) Resolve link target, handling absolute and relative (from global_link's dir)
		if os.path.islink(global_link):
			target = os.readlink(global_link)
			if os.path.isabs(target):
				# absolute symlink
				resolved = target
			else:
				# relative to the directory containing the symlink
				base = os.path.dirname(global_link)
				resolved = os.path.join(base, target)
			cache_dir = os.path.realpath(resolved)

		elif os.path.isdir(global_link):
			# someone recreated the dir instead of symlink
			cache_dir = global_link

		else:
			# not yet created → point at the expected symlink path
			cache_dir = global_link

		# 4) Remember for _cache_live()
		self.layer_hash = master_hash
		self.cache_dir = cache_dir

		# 5) Sanity‐check cache_root exists
		if not os.path.isdir(cache_root):
			L.critical("Cache root '{}' not found, exiting.".format(cache_root))
			raise SystemExit(1)

		# 6) Warn if no snapshot directory is present yet
		if not os.path.isdir(self.cache_dir):
			L.warning(
				"No cache snapshot for URI '{}' at '{}'.".format(uri, self.cache_dir)
			)

		# 7) Delegate to FileSystemLibraryProvider
		cache_uri = "file://{}".format(self.cache_dir.rstrip("/"))
		super().__init__(library, cache_uri, layer, set_ready=False)
		library.App.PubSub.subscribe("library.cache.ready", self._on_cache_ready)



	async def _on_cache_ready(self, *args):
		await self._set_ready()

	def _cache_live(self):
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
