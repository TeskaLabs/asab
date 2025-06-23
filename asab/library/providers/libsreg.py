import os.path
import lzma
import logging
import hashlib
import random
import tarfile
import asyncio
import shutil
import tempfile
import typing
import urllib.parse

import aiohttp

from .filesystem import FileSystemLibraryProvider
from ..dirsync import synchronize_dirs
from ...utils import convert_to_seconds

#

L = logging.getLogger(__name__)

#


class LibsRegLibraryProvider(FileSystemLibraryProvider):
	"""
	Read-only provider to read from remote "library repository".

	It provides an option to specify more servers for more reliable content delivery.

	Configuration example:

	```ini
	[library]
	providers=
		...
		libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library
		...
	```

	Specify the library version in the URL fragment (after `#`), the default is `production`:
	```ini
	[library]
	providers=
		...
		libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library#v25.14.01
		...
	```

	Specify the pull interval after `#pull=`:
	```ini
	[library]
	providers=
		...
		libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library#v25.14.01#pull=24h  ; v25.14.01, 24 hours
		libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library#pull=30m  ; production, 30 minutes
		...
	```
	"""


	def __init__(self, library, path, layer):

		url = urllib.parse.urlparse(path)
		assert url.scheme.startswith("libsreg+")

		fragment = url.fragment

		version = ""
		pull_interval = None

		# Split fragment by '#' and process parts
		if fragment:
			parts = fragment.split('#')
			for part in parts:
				if part.startswith("pull="):
					pull_interval = part[5:]
				elif part:
					version = part

		if pull_interval is not None:
			self.PullInterval = convert_to_seconds(pull_interval)
		else:
			self.PullInterval = 43200  # Default pull interval is 12 hours

		if version == "":
			version = "production"

		archname = url.path[1:]

		self.URLs = ["{scheme}://{netloc}/{archname}/{archname}-{version}.tar.xz".format(
			scheme=url.scheme[8:],
			netloc=netloc,
			archname=archname,
			version=version,
		) for netloc in url.netloc.split(",")]
		assert len(self.URLs) > 0

		# TODO: Read this for `[general]` config
		self.TrustEnv = True

		tempdir = tempfile.gettempdir()
		self.RootPath = os.path.join(
			tempdir,
			"asab.library.libsreg",
			hashlib.sha256(path.encode("utf-8")).hexdigest()
		)

		self.RepoPath = os.path.join(
			self.RootPath,
			"content"
		)


		os.makedirs(os.path.join(self.RepoPath), exist_ok=True)

		super().__init__(library, self.RepoPath, layer, set_ready=False)

		self.PullLock = asyncio.Lock()
		self.LastPull = None

		# TODO: Subscription to changes in the library
		self.SubscribedPaths = set()

		self.App.TaskService.schedule(self._periodic_pull(None))
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute.
		`PullLock` ensures that only if previous "pull" has finished, new one can start.

		Uses E-Tags for caching and retries different URLs to fetch the latest version.
		"""

		if self.PullLock.locked():
			return

		if self.LastPull is not None and self.App.time() - self.LastPull < self.PullInterval:
			# Do not pull if the last pull was done less than PullInterval ago
			return

		async with self.PullLock:
			await self._do_pull()
			self.LastPull = self.App.time()

	async def _do_pull(self):
		headers = {}

		# Check for existing E-Tag
		etag_fname = os.path.join(self.RootPath, "etag")
		if os.path.exists(etag_fname):

			# Count number of files in self.RootPath recursively
			file_count = sum([len(files) for _, _, files in os.walk(self.RootPath)])

			# If less than 5 files, we ignore the E-Tag and re-download everything
			if file_count > 5:
				with open(etag_fname, "r") as f:
					etag = f.read().strip()
					headers["If-None-Match"] = etag

		# Prepare a list of URLs to try
		# Randomize the order of the URLs (there might be more than one server to try)
		# The list is trippled to increase the chance of getting the new version
		# None is used as a separator between the URL sets - if the first URL set fails, we wait for 5 seconds before trying the next one
		urllist = self.URLs.copy()
		random.shuffle(urllist)
		urllist = urllist + [None] + urllist + [None] + urllist

		for i in range(len(urllist)):
			url = urllist[i]

			if url is None:
				# Sleep for 5 seconds before trying the next URL set
				await asyncio.sleep(5)
				continue

			L.debug("Periodic pull of libsreg library", struct_data={"url": url})

			last_try = i == len(urllist) - 1

			try:
				# This is a hotfix at 02/06/2025
				# Some SSL servers do not properly complete SSL shutdown process,
				# in that case asyncio leaks SSL connections. If this parameter is set to True,
				# aiohttp additionally aborts underlining transport after 2 seconds. It is off by default.
				connector = aiohttp.TCPConnector(
					enable_cleanup_closed=True,
					force_close=True,  # Close underlying sockets after connection releasing
				)

				async with aiohttp.ClientSession(connector=connector, trust_env=self.TrustEnv) as session:
					async with session.get(url, headers=headers) as response:

						if response.status == 200:  # The request indicates a new version that we don't have yet

							etag_incoming = response.headers.get('ETag')

							# Download new version
							dwnld_size = 0
							newtarfname = os.path.join(self.RootPath, "new.tar.xz")
							with open(newtarfname, 'wb') as ftmp:
								while True:
									chunk = await response.content.read(16 * 1024)
									if not chunk:
										break
									ftmp.write(chunk)
									dwnld_size += len(chunk)

							# Extract the contents to the temporary directory
							temp_extract_dir = os.path.join(
								self.RootPath,
								"new"
							)

							# Remove temp_extract_dir if it exists (from the last, failed run)
							if os.path.exists(temp_extract_dir):
								shutil.rmtree(temp_extract_dir)

							# Extract the archive into the temp_extract_dir
							try:
								with tarfile.open(newtarfname, mode='r:xz') as tar:
									tar.extractall(temp_extract_dir)
							except lzma.LZMAError:
								L.exception("LZMAError", struct_data={'size': dwnld_size})
								continue

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

							L.debug("Library updated from remote repository.", struct_data={"url": url, 'size': dwnld_size, 'etag': etag_incoming})
							return  # We are done, leaving the loop

						elif response.status == 304:
							# The repository has not changed ...
							if not self.IsReady:
								await self._set_ready()

							return  # We are done, leaving the loop

						else:
							if last_try:
								L.error("Failed to download the library.", struct_data={"url": url, 'status': response.status})

			except aiohttp.ClientError as e:
				if last_try:
					L.error("Failed to download the library (ClientError).", struct_data={"url": url, 'error': e, 'exception': e.__class__.__name__})

			except asyncio.TimeoutError as e:
				if last_try:
					L.error("Failed to download the library (TimeoutError).", struct_data={"url": url, 'error': e, 'exception': e.__class__.__name__})

			except Exception:
				L.exception("Error when fetching the library content from a registry")

	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		self.SubscribedPaths.add(path)
