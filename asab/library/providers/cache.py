import os
import logging
import hashlib

from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.config import Config

L = logging.getLogger(__name__)

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

    async def read(self, path):
        # FALLBACK only if the entire cache folder is gone
        if not os.path.isdir(self.cache_dir):
            return await self._real.read(path)
        # otherwise serve from cache (None on missing file → next provider)
        return await super().read(path)

    async def list(self, path):
        # FALLBACK only if the entire cache folder is gone
        if not os.path.isdir(self.cache_dir):
            return await self._real.list(path)
        # otherwise serve from cache (KeyError on missing dir → next provider)
        return await super().list(path)
