import os
import logging
import hashlib
import random
import tarfile
import asyncio
import shutil
import tempfile
import urllib.parse

import aiohttp

from .filesystem import FileSystemLibraryProvider
from ..dirsync import synchronize_dirs

#

L = logging.getLogger(__name__)

#


class LibsRegLibraryProvider(FileSystemLibraryProvider):
	"""
	Read-only provider to read from remote "library repository".

	It provides an option to specify more servers for more reliable content delivery.

	Example of the configuration:

	```ini
	[library]
	providers=
	...
	libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library
	...
	```

	"""

	def __init__(self, library, path, layer):

		url = urllib.parse.urlparse(path)
		assert url.scheme.startswith('libsreg+')

		version = url.fragment
		if version == '':
			version = 'production'

		archname = url.path[1:]

		self.URLs = ["{scheme}://{netloc}/{archname}/{archname}-{version}.tar.xz".format(
			scheme=url.scheme[8:],
			netloc=netloc,
			archname=archname,
			version=version,
		) for netloc in url.netloc.split(',')]
		assert len(self.URLs) > 0

		tempdir = tempfile.gettempdir()
		self.RootPath = os.path.join(
			tempdir,
			"asab.library.libsreg",
		)

		self.RepoPath = os.path.join(
			self.RootPath,
			hashlib.sha256(self.URLs[0].encode('utf-8')).hexdigest()
		)

		os.makedirs(os.path.join(self.RepoPath), exist_ok=True)

		super().__init__(library, self.RepoPath, layer, set_ready=False)

		self.PullLock = asyncio.Lock()

		# TODO: Subscribption to changes in the library
		self.SubscribedPaths = set()

		self.App.TaskService.schedule(self._periodic_pull(None))
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute.
		`PullLock` ensures that only if previous "pull" has finished, new one can start.
		"""

		if self.PullLock.locked():
			return

		async with self.PullLock:
			headers = {}

			# Check for existing E-Tag
			etag_fname = os.path.join(self.RootPath, "etag")
			try:
				with open(etag_fname, 'r') as f:
					etag = f.read().strip()
					headers['If-None-Match'] = etag
			except FileNotFoundError:
				pass

			url = random.choice(self.URLs)

			try:
				async with aiohttp.ClientSession() as session:
					async with session.get(url, headers=headers) as response:

						if response.status == 200:  # The request indicates a new version that we don't have yet

							etag_incoming = response.headers.get('ETag')

							# Download new version
							newtarfname = os.path.join(self.RootPath, "new.tar.xz")
							with open(newtarfname, 'wb') as ftmp:
								while True:
									chunk = await response.content.read(16 * 1024)
									if not chunk:
										break
									ftmp.write(chunk)

							# Extract the contents to the temporary directory
							temp_extract_dir = os.path.join(
								self.RootPath,
								"new"
							)

							# Remove temp_extract_dir if it exists (from the last, failed run)
							if os.path.exists(temp_extract_dir):
								shutil.rmtree(temp_extract_dir)

							# Extract the archive into the temp_extract_dir
							with tarfile.open(newtarfname, mode='r:xz') as tar:
								tar.extractall(temp_extract_dir)

							# Synchronize the temp_extract_dir into the library
							synchronize_dirs(self.RepoPath, temp_extract_dir)
							if not self.IsReady:
								await self._set_ready()

							if etag_incoming is not None:
								with open(etag_fname, 'w') as f:
									f.write(etag_incoming)

							# Remove temp_extract_dir
							if os.path.exists(temp_extract_dir):
								shutil.rmtree(temp_extract_dir)

							# Remove newtarfname
							if os.path.exists(newtarfname):
								os.remove(newtarfname)

						elif response.status == 304:
							# The repository has not changed ...
							if not self.IsReady:
								await self._set_ready()

						else:
							L.error("Failed to download the library.", struct_data={"url": url, 'status': response.status})

			except aiohttp.ClientError as e:
				L.error("Failed to download the library (ClientError).", struct_data={"url": url, 'error': e, 'exception': e.__class__.__name__})

			except asyncio.TimeoutError as e:
				L.error("Failed to download the library (TimeoutError).", struct_data={"url": url, 'error': e, 'exception': e.__class__.__name__})


	async def subscribe(self, path):
		self.SubscribedPaths.add(path)
