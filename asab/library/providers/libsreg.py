import os
import logging
import hashlib
import shutil
import random
import tarfile
import tempfile
import urllib.parse

import aiohttp

from ...config import Config
from .filesystem import FileSystemLibraryProvider
from ..dirsync import synchronize_dirs

#

L = logging.getLogger(__name__)

#
Config.add_defaults(
	{
		'library': {
			# You may specify multiple ElasticSearch nodes by e.g. http://es01:9200,es02:9200,es03:9200/
			'repo_sub_path': '/'
		}
	}
)


class LibsRegLibraryProvider(FileSystemLibraryProvider):
	"""
	Read-only provider to read from remote "library repository".

	It provides an option to specify more servers for more reliable content delivery.

	Example of the configuration:

	```ini
	[library]
	providers=
	...
	libsreg+https://libsreg.z6.web.core.windows.net,libsreg-secondary.z6.web.core.windows.net/lmio-common-library
	...
	```

	"""

	def __init__(self, library, path, layer):

		url = urllib.parse.urlparse(path)
		assert url.scheme.startswith('libsreg+')

		version = url.fragment
		if version == '':
			version = 'master'

		archname = url.path[1:]

		self.URLs = ["{scheme}://{netloc}/{archname}/{archname}-{version}.tar.xz".format(
			scheme=url.scheme[8:],
			netloc=netloc,
			archname=archname,
			version=version,
		) for netloc in url.netloc.split(',')]
		assert len(self.URLs) > 0

		tempdir = tempfile.gettempdir()
		self.RepoSubPath = Config.get('library', 'repo_sub_path')
		self.RepoPath = os.path.join(
			tempdir,
			"asab.library.libsreg",
			hashlib.sha256(self.URLs[0].encode('utf-8')).hexdigest()
		)

		if self.RepoSubPath == "/":
			# No additional subdirectory, use the base directory as is.
			self.FinalPath = self.RepoPath
		else:
			# Append the subdirectory to the base path and create it.
			self.FinalPath = os.path.join(self.RepoPath, self.RepoSubPath)

		# Ensure the directory exists
		os.makedirs(self.FinalPath, exist_ok=True)

		super().__init__(library, self.RepoPath, layer, set_ready=False)

		self.PullLock = False

		# TODO: Subscription to changes in the library
		self.SubscribedPaths = set()

		self.App.TaskService.schedule(self._periodic_pull(None))
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute. `PullLock` flag ensures that only if previous "pull" has finished, new one can start.
		"""
		if self.PullLock:
			return

		self.PullLock = True

		try:
			headers = {}

			# Check for existing E-Tag
			etag_fname = os.path.join(self.RepoPath, "etag")
			try:
				with open(etag_fname, 'r') as f:
					etag = f.read().strip()
					headers['If-None-Match'] = etag
			except FileNotFoundError:
				pass

			url = random.choice(self.URLs)

			async with aiohttp.ClientSession() as session:
				async with session.get(url, headers=headers) as response:

					if response.status == 200:  # The request indicates a new version that we don't have yet

						etag_incoming = response.headers.get('ETag')

						fname = os.path.join(self.RepoPath, "new.tar.xz")
						with open(fname, 'wb') as ftmp:
							while True:
								chunk = await response.content.read(16 * 1024)
								if not chunk:
									break
								ftmp.write(chunk)

						# TODO: Following code is potentionally blocking and should be done in a proactor
						# ⬇️⬇️⬇️ ---------- START OF THE BLOCKING CODE

						with tarfile.open(fname, mode='r:xz') as tar:
							tar.extractall(os.path.join(self.RepoPath, "new"))

						os.unlink(fname)

						# Move the new content in place
						synchronize_dirs(self.FinalPath, os.path.join(self.RepoPath, "new"))
						shutil.rmtree(os.path.join(self.RepoPath, "new"))

						if etag_incoming is not None:
							with open(etag_fname, 'w') as f:
								f.write(etag_incoming)

						# ⬆️⬆️⬆️ --------- END OF THE BLOCKING CODE

					elif response.status == 304:
						# The repository has not changed ...
						pass

					else:
						L.exception("Failed to download the library.", struct_data={"url": url, 'status': response.status})

		finally:
			self.PullLock = False


	async def subscribe(self, path):
		self.SubscribedPaths.add(path)
