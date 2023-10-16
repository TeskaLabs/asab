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
			'repo_sub_path': '/'
		}
	}
)


class LibsRegLibraryProvider(FileSystemLibraryProvider):

	def __init__(self, library, path, layer):

		url = urllib.parse.urlparse(path)
		assert url.scheme.startswith('libsreg+')

		version = url.fragment if url.fragment else 'master'
		archname = url.path[1:]

		self.URLs = ["{scheme}://{netloc}/{archname}/{archname}-{version}.tar.xz".format(
			scheme=url.scheme[8:],
			netloc=netloc,
			archname=archname,
			version=version,
		) for netloc in url.netloc.split(',')]
		assert len(self.URLs) > 0

		tempdir = tempfile.gettempdir()
		self.RepoPath = os.path.join(
			tempdir,
			"asab.library.libsreg",
			hashlib.sha256(self.URLs[0].encode('utf-8')).hexdigest()
		)

		# Ensure the base repository path exists
		os.makedirs(self.RepoPath, exist_ok=True)

		# Determine the final path based on the configuration
		repo_sub_path = Config.get('library', 'repo_sub_path')
		self.FinalPath = os.path.join(self.RepoPath, repo_sub_path.strip("/")) if repo_sub_path != "/" else self.RepoPath

		# Ensure the final path exists
		os.makedirs(self.FinalPath, exist_ok=True)

		super().__init__(library, self.RepoPath, layer, set_ready=False)

		self.PullLock = False
		self.SubscribedPaths = set()

		self.App.TaskService.schedule(self._periodic_pull(None))
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)

	async def _periodic_pull(self, event_name):
		if self.PullLock:
			return

		self.PullLock = True

		try:
			headers = {}
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

					if response.status == 200:
						etag_incoming = response.headers.get('ETag')

						# Ensure the new directory exists before writing the file
						new_dir = os.path.join(self.RepoPath, "new")
						os.makedirs(new_dir, exist_ok=True)

						fname = os.path.join(new_dir, "new.tar.xz")
						with open(fname, 'wb') as ftmp:
							while True:
								chunk = await response.content.read(16 * 1024)
								if not chunk:
									break
								ftmp.write(chunk)

						with tarfile.open(fname, mode='r:xz') as tar:
							tar.extractall(new_dir)

						os.unlink(fname)

						# Synchronize the directories
						synchronize_dirs(self.FinalPath, new_dir)
						# Safely remove the new directory if it exists
						if os.path.exists(new_dir):
							shutil.rmtree(new_dir)
						else:
							L.warning("Directory not found for removal: {}".format(new_dir))

					if etag_incoming is not None:
							with open(etag_fname, 'w') as f:
								f.write(etag_incoming)

					elif response.status == 304:
						pass  # No changes

					else:
						L.exception("Failed to download the library.", struct_data={"url": url, 'status': response.status})

		finally:
			self.PullLock = False

	async def subscribe(self, path):
		self.SubscribedPaths.add(path)
