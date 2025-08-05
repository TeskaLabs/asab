import os
import logging
import hashlib

from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.config import Config

##

L = logging.getLogger(__name__)


##


class CacheLibraryProvider(FileSystemLibraryProvider):
	"""
	A read‐only cache wrapper that points at
	[library:cache].dir/@global/<layer_hash>.

	Any call to read()/list() will serve from cache if present,
	or return None if the cache is missing.
	"""

	def __init__(self, library, uri, layer):
		# Compute layer hash INSIDE the provider
		self.layer_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()

		# Resolve cache root
		cache_root = Config.get("library:cache", "dir", fallback=None)
		if not cache_root:
			raise RuntimeError("Missing [library:cache].dir configuration")
		if not os.path.isdir(cache_root):
			L.critical("Cache root '{}' not found, exiting.".format(cache_root))
			raise SystemExit(1)

		# Compose live cache snapshot directory
		self.cache_dir = os.path.join(cache_root, "@global", self.layer_hash)
		if not os.path.isdir(self.cache_dir):
			L.warning(
				"No cache snapshot for URI '{}' at '{}'.".format(uri, self.cache_dir)
			)

		cache_uri = "file://{}".format(self.cache_dir.rstrip("/"))
		super().__init__(library, cache_uri, layer, set_ready=False)
		library.App.PubSub.subscribe("library.cache.ready", self._on_cache_ready)

	async def _on_cache_ready(self, *args):
		await self._set_ready()

	def _cache_live(self):
		return os.path.isdir(self.cache_dir)

	async def read(self, path):
		if self._cache_live():
			return await super().read(path)
		return None

	async def list(self, path):
		if self._cache_live():
			return await super().list(path)
		return None

	async def find(self, path):
		if self._cache_live():
			return await super().find(path)
		return None

	async def subscribe(self, path, target=None):
		if self._cache_live():
			return await super().subscribe(path, target)
		return None
