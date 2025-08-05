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

    Any cache miss (missing dir or file) simply returns None
    or raises KeyError so that LibraryService will fall through
    to the next provider.
    """

    def __init__(self, library, uri, layer):
        # compute the symlink key
        self.layer_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()

        # resolve cache root
        cache_root = Config.get("library:cache", "dir", fallback=None)
        if not cache_root:
            raise RuntimeError("Missing [library:cache].dir configuration")
        if not os.path.isdir(cache_root):
            L.critical("Cache root '{0}' not found, exiting.".format(cache_root))
            raise SystemExit(1)

        # point at the live snapshot
        cache_dir = os.path.join(cache_root, "@global", self.layer_hash)
        if not os.path.isdir(cache_dir):
            L.warning("No cache snapshot for URI '{0}' at '{1}'.".format(uri, cache_dir))

        # filesystem-style URI
        cache_uri = "file://{0}".format(cache_dir.rstrip("/"))
        super().__init__(library, cache_uri, layer, set_ready=False)

        # re-publish readiness when the cache updates
        library.App.PubSub.subscribe("library.cache.ready", self._on_cache_ready)

    async def _on_cache_ready(self, *args):
        # once a new snapshot appears, mark ready
        await self._set_ready()
