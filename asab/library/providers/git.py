import tempfile
import logging
import os
import shutil

import pygit2

from .filesystem import FileSystemLibraryProvider
from ...config import Config

#

L = logging.getLogger(__name__)

#


class GitLibraryProvider(FileSystemLibraryProvider):
	"""
	Read-only git provider to read from remote repository.
	It clones a remote git repository to a temporary directory and then uses the
	FileSystemLibraryProvider to read the files.
	To read from local git repository, please use FileSystemProvider.

	Configuration:
	(Use either deploytoken, publickey+privatekey for SSH option, or username and password and HTTP access.)
	```
	[library]
	providers=git+<URL or deploy token>

	[library:git]
	publickey=<absolute path to file>
	privatekey=<absolute path to file>
	username=johnsmith
	password=secretpassword
	```
	"""
	def __init__(self, library, path):
		self.LastCommit = None
		self.URL = path[4:]
		self.Callbacks = pygit2.RemoteCallbacks(get_git_credentials(self.URL))
		self.RepoPath = tempfile.TemporaryDirectory().name
		self.GitRepository = pygit2.clone_repository(self.URL, self.RepoPath, callbacks=self.Callbacks)
		self._check_remote()
		super().__init__(library, self.RepoPath)

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")

		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def finalize(self, app):
		clean_path(self.RepoPath)

	async def pull(self):
		"""
		Equivalent to `git pull` command.
		"""
		commit_id = await self.ProactorService.execute(fetch, self.GitRepository, self.Callbacks)
		if commit_id == self.LastCommit:
			return
		await self.ProactorService.execute(merge, self.GitRepository, commit_id)

	def _periodic_pull(self, event_name):
		self.pull()

	def _check_remote(self):
		try:
			assert self.GitRepository.remotes["origin"] is not None
		except (KeyError, AssertionError):
			L.critical("Connection to remote git repository failed.")
			raise SystemExit("Application exiting...")
		try:
			self.LastCommit = fetch(self.GitRepository, self.Callbacks)
		except Exception as e:
			L.warning("Git Provider cannot fetch from remote repository. Error: {}".format(e))
			raise SystemExit("Application exiting...")

	async def list(self, path: str) -> list:
		return await super().list(path)


def fetch(repository, callbacks):
	"""
	It fetches the remote repository and returns the commit ID of the remote HEAD

	:param repository: The repository object that you want to fetch from
	:param callbacks: A dictionary of callbacks to be used during the fetch
	:return: The commit id of the latest commit on the remote repository.
	"""
	repository.remotes["origin"].fetch(callbacks=callbacks)
	reference = repository.lookup_reference("refs/remotes/origin/HEAD")
	commit_id = reference.peel().id
	return commit_id


def merge(repository, commit_id):
	repository.merge(commit_id)


def get_git_credentials(url):
	"""
	Returns a pygit2.Credentials object that can be used to authenticate with the git repository

	:param url: The URL of the repository you want to clone
	:return: A pygit2.Keypair object or a pygit2.UserPass object
	"""
	username = Config.get("library:git", "username", fallback=None)
	password = Config.get("library:git", "password", fallback=None)
	publickey = Config.get("library:git", "publickey", fallback=None)
	privatekey = Config.get("library:git", "privatekey", fallback=None)

	if publickey is not None and privatekey is not None:
		return pygit2.Keypair(username_from_url(url), publickey, privatekey, "")

	elif username is not None and password is not None:
		return pygit2.UserPass(username, password)


def username_from_url(url):
	return url.split("@")[0]


def clean_path(path):
	"""
	It deletes a folder and all its contents

	:param path: The path to the directory to be deleted
	"""
	if os.path.isdir(path):
		try:
			for root, dirs, files in os.walk(path):
				for f in files:
					os.unlink(os.path.join(root, f))
				for d in dirs:
					shutil.rmtree(os.path.join(root, d))
			os.removedirs(path)
		except OSError as e:
			L.error("Error when deleting folder: %s - %s." % (e.filename, e.strerror))
