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
    A read-only cache-backed wrapper that serves from the on-disk cache,
    and only on I/O errors (“hard” failures) will cascade to the real provider.

    Under [library:cache].dir, each layer is exposed via:
      @global/<layer_hash>/...
    where layer_hash = sha256(uri).

    Usage (in LibraryService._create_library):
        real = LibsRegLibraryProvider(...)
        cache = CacheLibraryProvider(library, uri, layer, real)
        self.Libraries.append(cache)

    On every read()/list():
     1. Try cache
     2. If it throws, fall back to real.read()/real.list()
    """

    def __init__(self, library, uri, layer, real_provider):
        # Keep for fallback
        self._real = real_provider
        self.uri = uri
        self.layer_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()

        # 1) Validate cache root
        cache_root = Config.get("library:cache", "dir", fallback=None)
        if not cache_root:
            raise Exception(
                "Missing [library:cache].dir configuration"
            )
        if not os.path.isdir(cache_root):
            L.critical("Cache root %s not found, exiting.", cache_root)
            raise SystemExit("Missing cache root")

        # 2) Build the cache URI
        self.cache_dir = os.path.join(cache_root, "@global", self.layer_hash)
        if not os.path.isdir(self.cache_dir):
            L.warning("Cache directory not found for %s: %s", uri, self.cache_dir)

        cache_uri = "file://" + self.cache_dir.rstrip("/")
        # Initialize the filesystem provider *only* against the cache
        super().__init__(library, cache_uri, layer, set_ready=False)

        # 3) Re-publish readiness when new snapshots arrive
        library.App.PubSub.subscribe(
            "library.cache.ready",
            self._on_cache_ready
        )

    async def _on_cache_ready(self, event, data):
        await self._set_ready()

    async def read(self, path):
        if not os.path.isdir(self.cache_dir):
            # ← cache folder doesn’t exist → fall back
            return await self._real.read(path)
        return await super().read(path)

    async def list(self, path):
        if not os.path.isdir(self.cache_dir):
            return await self._real.list(path)
        return await super().list(path)
