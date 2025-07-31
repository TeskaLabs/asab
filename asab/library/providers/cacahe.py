import os
import logging
import hashlib

from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.config import Config
from asab import exceptions

L = logging.getLogger(__name__)

class CacheLibraryProvider(FileSystemLibraryProvider):
    """
    A read-only cache-backed wrapper that serves exclusively from the on-disk cache.
    No fallback to upstream providers; cache misses return None or empty list.

    Under [library:cache].dir, each layer is exposed via:
      @global/<layer_hash>/...
    where layer_hash = sha256(uri).

    Usage (registering provider in LibraryService._create_library):
        provider = CacheLibraryProvider(library, uri, layer)

    Consuming cached layers:
    1. Ensure LibraryCacheService has populated the cache and published 'library.cache.ready'.
    2. LibraryService will wrap each 'libsreg+' URI with this CacheLibraryProvider.
    3. To read an item:
       ```python
       async with library.open('/path/to/item') as stream:
           if stream is None:
               # cache miss or not found
               return None
           data = stream.read()
       ```
    4. To list contents of a directory:
       ```python
       items = await library.list('/path/to/directory/')
       for item in items:
           print(item.name)
       ```

    Layer directories on disk:
      [cache_root]/@cache/<unique_id>/            # immutable snapshots
      [cache_root]/@cache/<unique_id>/.uri         # original URI
      [cache_root]/@cache/<unique_id>/.unique_id   # snapshot hash
      [cache_root]/@global/<layer_hash>/           # symlink to active snapshot
      [cache_root]/@global/<layer_hash>/.uri
      [cache_root]/@global/<layer_hash>/.unique_id

    Notes for GitLab Merge Request:
    - This change introduces a CacheLibraryProvider to serve from disk-only cache.
    - Ensure `[library:cache].dir` is documented in configuration reference.
    - Update LibraryService to wrap `libsreg+` URIs with this provider instead of direct network fetch.
    - Add integration test to verify cache lookup and symlink resolution.
    - Confirm backward compatibility: providers other than `libsreg+` remain unaffected.
    - Mention atomic symlink swap behavior in release notes.
    """
    def __init__(self, library, uri, layer):
        # Compute stable layer key
        self.uri = uri
        self.layer_hash = hashlib.sha256(uri.encode('utf-8')).hexdigest()

        # Locate configured cache root
        cache_root = Config.get('library:cache', 'dir', fallback=None)
        if not cache_root:
            raise exceptions.LibraryConfigurationError(
                "Missing [library:cache].dir configuration"
            )

        # Build path to on-disk cache for this layer
        self.cache_dir = os.path.join(cache_root, '@global', self.layer_hash)
        if not os.path.isdir(self.cache_dir):
            L.warning("Cache directory not found for %s: %s", uri, self.cache_dir)

        # Initialize filesystem provider against cache path, skip ready event
        cache_uri = 'file://' + self.cache_dir.rstrip('/')
        super().__init__(library, cache_uri, layer, set_ready=False)

    # Override read/list to serve only from cache
    async def read(self, path):
        """
        Attempt to read from cache; return None on cache miss.

        :param path: Absolute path within the library (e.g. '/Templates/config.json')
        :returns: File-like stream or None
        """
        return await super().read(path)

    async def list(self, path):
        """
        Attempt to list directory from cache; return empty list on cache miss.

        :param path: Absolute directory path (e.g. '/Templates/')
        :returns: List of LibraryItem objects
        """
        try:
            return await super().list(path)
        except Exception:
            L.warning("Cache list miss or error: %s", path)
            return []
