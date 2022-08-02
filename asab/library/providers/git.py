import os
import tempfile
import logging
import hashlib

from .filesystem import FileSystemLibraryProvider
from ...config import Config

#

L = logging.getLogger(__name__)

#

try:
	import pygit2
except ImportError:
	L.critical("Please install pygit2 package to enable Git Library Provider. >>> pip install pygit2")
	raise SystemExit("Application exiting... .")


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
	repodir=<optional location of the repository cache>
	branch=<optional remote branch name>
	```
	"""
	def __init__(self, library, path):
		self.LastCommit = None
		self.URL = path[4:]

		self.Callbacks = pygit2.RemoteCallbacks(get_git_credentials(self.URL))
		self.Branch = Config.get("library:git", "branch", fallback="HEAD")

		repodir = Config.get("library:git", "repodir", fallback=None)
		if repodir is not None:
			self.RepoPath = os.path.abspath(repodir)
		else:
			tempdir = tempfile.gettempdir()
			self.RepoPath = os.path.join(
				tempdir,
				"asab.library.git",
				hashlib.sha256(self.URL.encode('utf-8')).hexdigest()
			)

		super().__init__(library, self.RepoPath, waiting_for_git=True)

		self.App.TaskService.schedule(self.intialize_git_repo())

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")

		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def pull(self):
		"""
		Equivalent to `git pull` command.
		"""
		if await self.check_update():
			await self.ProactorService.execute(merge, self.GitRepository, self.LastCommit)


	async def check_update(self):
		commit_id = await self.ProactorService.execute(fetch, self.GitRepository, self.Callbacks, self.Branch)
		if commit_id == self.LastCommit:
			return False
		self.LastCommit = commit_id
		return True


	async def _periodic_pull(self, event_name):
		await self.pull()


	async def intialize_git_repo(self):
		await self.ProactorService.execute(self._initialize_git_repo)
		await self._set_ready()

	def _initialize_git_repo(self):
		if pygit2.discover_repository(self.RepoPath) is None:
			os.makedirs(self.RepoPath, mode=0o700)
			if self.Branch == "HEAD":
				self.GitRepository = pygit2.clone_repository(self.URL, self.RepoPath, callbacks=self.Callbacks)
			else:
				self.GitRepository = pygit2.clone_repository(self.URL, self.RepoPath, callbacks=self.Callbacks, checkout_branch=self.Branch)
		else:
			self.GitRepository = pygit2.Repository(self.RepoPath)

		try:
			assert self.GitRepository.remotes["origin"] is not None
		except (KeyError, AssertionError):
			L.critical("Connection to remote git repository failed.")
			raise SystemExit("Application exiting...")

		try:
			self.LastCommit = fetch(self.GitRepository, self.Callbacks, self.Branch)
		except Exception as e:
			L.critical("Git Provider cannot fetch from remote repository. Error: {}".format(e))
			raise SystemExit("Application exiting...")

		try:
			merge(self.GitRepository, self.LastCommit)
		except Exception as e:
			L.critical("Git Provider cannot merge remote HEAD with local repository. Error: {}".format(e))
			raise SystemExit("Application exiting...")



def fetch(repository, callbacks, branch):
	"""
	It fetches the remote repository and returns the commit ID of the remote HEAD

	:param repository: The repository object that you want to fetch from
	:param callbacks: A dictionary of callbacks to be used during the fetch
	:return: The commit id of the latest commit on the remote repository.
	"""
	repository.remotes["origin"].fetch(callbacks=callbacks)
	reference = repository.lookup_reference("refs/remotes/origin/{}".format(branch))
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
