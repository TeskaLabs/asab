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

    Any call to read()/list() will:
      – if the cache directory doesn’t exist → fall back to real provider
      – otherwise → serve from cache and let misses bubble up
    """

    def __init__(self, library, uri, layer, real_provider):
        # Keep for fallback
        self._real = real_provider
        # Compute layer‐key
        self.layer_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()

        # Resolve cache root
        cache_root = Config.get("library:cache", "dir", fallback=None)
        if not cache_root:
            raise RuntimeError("Missing [library:cache].dir configuration")
        if not os.path.isdir(cache_root):
            L.critical("Cache root '{0}' not found, exiting.".format(cache_root))
            raise SystemExit(1)

        # Point at the *live* cache snapshot
        self.cache_dir = os.path.join(cache_root, "@global", self.layer_hash)
        if not os.path.isdir(self.cache_dir):
            L.warning("No cache snapshot for URI '{0}' at '{1}'.".format(uri, self.cache_dir))

        # Filesystem‐style URI for the cache
        cache_uri = "file://{0}".format(self.cache_dir.rstrip("/"))
        super().__init__(library, cache_uri, layer, set_ready=False)

        # Whenever the cache service signals ready, re‐publish readiness
        library.App.PubSub.subscribe("library.cache.ready", self._on_cache_ready)

    async def _on_cache_ready(self, *args):
        await self._set_ready()

    def _cache_live(self):
        # True once @global/<layer_hash> exists
        return os.path.isdir(self.cache_dir)

    async def read(self, path):
        if self._cache_live():
            return await super().read(path)
        return await self._real.read(path)

    async def list(self, path):
        if self._cache_live():
            return await super().list(path)
        return await self._real.list(path)

    async def find(self, path):
        if self._cache_live():
            return await super().find(path)
        return await self._real.find(path)

    async def subscribe(self, path, target=None):
        # subscribe *only* where we actually expect changes
        if self._cache_live():
            return await super().subscribe(path, target)
        return await self._real.subscribe(path, target)
