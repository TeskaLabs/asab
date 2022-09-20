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
	providers=git+<URL or deploy token>#<branch name>

	[library:git]
	publickey=<absolute path to file>
	privatekey=<absolute path to file>
	username=johnsmith
	password=secretpassword
	repodir=<optional location of the repository cache>
	```
	"""
	def __init__(self, library, path):

		# The branch can be optionally specified in the URL fragment (after '#')
		split_path = path.split("#", 1)
		if len(split_path) > 1:
			self.Branch = split_path[-1]
			self.URL = split_path[0][4:]
		else:
			self.Branch = None
			self.URL = path[4:]

		self.Callbacks = pygit2.RemoteCallbacks(get_git_credentials(self.URL))

		repodir = Config.get("library:git", "repodir", fallback=None)
		if repodir is not None:
			self.RepoPath = os.path.abspath(repodir)
		else:
			tempdir = tempfile.gettempdir()
			self.RepoPath = os.path.join(
				tempdir,
				"asab.library.git",
				hashlib.sha256(path.encode('utf-8')).hexdigest()
			)

		super().__init__(library, self.RepoPath, set_ready=False)

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")
		self.PullLock = False

		self.App.TaskService.schedule(self.intialize_git_repo())
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute. `PullLock` flag ensures that only if previous "pull" has finished, new one can start.
		"""
		if self.PullLock:
			return

		self.PullLock = True

		try:
			await self.ProactorService.execute(self.pull)
		finally:
			self.PullLock = False


	async def intialize_git_repo(self):

		def init_task():
			if pygit2.discover_repository(self.RepoPath) is None:
				# For a new repository, clone the remote bit
				try:
					os.makedirs(self.RepoPath, mode=0o700)
				except FileExistsError:
					pass
				self.GitRepository = pygit2.clone_repository(self.URL, self.RepoPath, callbacks=self.Callbacks, checkout_branch=self.Branch)
			else:
				# For existing repository, pull the latest changes
				self.GitRepository = pygit2.Repository(self.RepoPath)
				self.pull()

		await self.ProactorService.execute(init_task)

		try:
			assert self.GitRepository.remotes["origin"] is not None
		except (KeyError, AssertionError):
			L.error("Connection to remote git repository failed.")
			# The library will not get ready ... maybe we can retry init_test() in a while
			return

		await self._set_ready()


	def fetch(self):
		"""
		It fetches the remote repository and returns the commit ID of the remote branch

		:return: The commit id of the latest commit on the remote repository.
		"""
		self.GitRepository.remotes["origin"].fetch(callbacks=self.Callbacks)
		if self.Branch is None:
			reference = self.GitRepository.lookup_reference("refs/remotes/origin/HEAD")
		else:
			reference = self.GitRepository.lookup_reference("refs/remotes/origin/{}".format(self.Branch))
		commit_id = reference.peel().id
		return commit_id


	def pull(self):

		new_commit_id = self.fetch()

		if new_commit_id == self.GitRepository.head.target:
			return

		self.GitRepository.head.set_target(new_commit_id)
		self.GitRepository.reset(new_commit_id, pygit2.GIT_RESET_HARD)
		self.App.PubSub.publish("GitProviderUpdated!", self)


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
