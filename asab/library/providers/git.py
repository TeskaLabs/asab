import os
import tempfile
import logging
import hashlib
import re

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

	.. code::

		[library]
		providers=git+<URL or deploy token>#<branch name>

		[library:git]
		repodir=<optional location of the repository cache>
	"""
	def __init__(self, library, path):

		# format: 'git+http[s]://[<username>:<deploy token>@]<url>[#<branch>]'
		pattern = re.compile(r"git\+(https?://)((.*):(.*)@)?([^#]*)(?:#(.*))?$")
		path_split = pattern.findall(path)[0]
		L.debug(path_split)
		self.URLScheme, self.UserInfo, self.User, self.DeployToken, self.URLPath, self.Branch = path_split
		self.URL = "".join([self.URLScheme, self.UserInfo, self.URLPath])
		self.Branch = self.Branch if self.Branch != '' else None

		print(self.URL)

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

		self.GitRepository = None

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")
		self.PullLock = False

		self.SubscribedPaths = set()

		self.App.TaskService.schedule(self.initialize_git_repository())
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute. `PullLock` flag ensures that only if previous "pull" has finished, new one can start.
		"""
		if self.GitRepository is None:
			return

		if self.PullLock:
			return

		self.PullLock = True

		try:
			to_publish = await self.ProactorService.execute(self._do_pull)
			# Once reset of the head is finished, PubSub message about the change in the subscribed directory gets published.
			for path in to_publish:
				self.App.PubSub.publish("Library.change!", self, path)
		except pygit2.GitError:
			L.warning("Periodic pull from the remote repository failed.")
		finally:
			self.PullLock = False


	async def initialize_git_repository(self):

		def init_task():
			if pygit2.discover_repository(self.RepoPath) is None:
				# For a new repository, clone the remote bit
				os.makedirs(self.RepoPath, mode=0o700, exist_ok=True)
				self.GitRepository = pygit2.clone_repository(
					url=self.URL,
					path=self.RepoPath,
					checkout_branch=self.Branch
				)
			else:
				# For existing repository, pull the latest changes
				self.GitRepository = pygit2.Repository(self.RepoPath)
				self._do_pull()

		try:
			await self.ProactorService.execute(init_task)

		except KeyError as err:
			pygit_message = str(err).replace('\"', '')
			if pygit_message == "'refs/remotes/origin/{}'".format(self.Branch):
				# branch does not exist
				L.exception(
					"Branch does not exist.",
					struct_data={
						"url": self.URLPath,
						"branch": self.Branch
					}
				)
			else:
				L.exception("Error when initializing git repository: {}".format(pygit_message))
			self.App.stop()  # NOTE: raising Exception doesn't exit the app

		except pygit2.GitError as err:
			pygit_message = str(err).replace('\"', '')
			if pygit_message == "unexpected http status code: 404":
				# repository not found
				L.exception(
					"Git repository not found.",
					struct_data={
						"url": self.URLPath
					}
				)
			elif pygit_message == "remote authentication required but no callback set":
				# either repository not found or authentication failed
				L.exception(
					"Authentication failed when initializing git repository.\n"
					"Check if the 'providers' option satisfies the format: 'git+<username>:<deploy token>@<URL>#<branch name>'",
					struct_data={
						"url": self.URLPath,
						"username": self.User,
						"deploy_token": self.DeployToken
					}
				)
			elif 'cannot redirect from':
				# bad URL
				L.exception(
					"Git repository not found.",
					struct_data={
						"url": self.URLPath
					}
				)
			elif 'Temporary failure in name resolution' in pygit_message:
				# Internet connection does
				L.exception(
					"Git repository not initialized: connection failed. Check your network connection.",
					struct_data={
						"url": self.URLPath
					}
				)
			else:
				L.exception("Git repository not initialized: {}".format(err))
			self.App.stop()

		except Exception as err:
			L.exception(err)

		assert self.GitRepository.remotes["origin"] is not None, "Git repository not initialized."
		await self._set_ready()


	def _do_fetch(self):
		"""
		It fetches the remote repository and returns the commit ID of the remote branch

		:return: The commit id of the latest commit on the remote repository.
		"""
		if self.GitRepository is None:
			return None

		self.GitRepository.remotes["origin"].fetch()
		if self.Branch is None:
			reference = self.GitRepository.lookup_reference("refs/remotes/origin/HEAD")
		else:
			reference = self.GitRepository.lookup_reference("refs/remotes/origin/{}".format(self.Branch))
		commit_id = reference.peel().id
		return commit_id


	def _do_pull(self):
		new_commit_id = self._do_fetch()
		if new_commit_id == self.GitRepository.head.target:
			return []

		# Before new head is set, check the diffs. If changes in subscribed directory occured, add path to "to_publish" list.
		to_publish = []
		for path in self.SubscribedPaths:
			for i in self.GitRepository.diff(self.GitRepository.head.target, new_commit_id).deltas:
				if ("/" + i.old_file.path).startswith(path):
					to_publish.append(path)

		# Reset HEAD
		self.GitRepository.head.set_target(new_commit_id)
		self.GitRepository.reset(new_commit_id, pygit2.GIT_RESET_HARD)

		return to_publish

	async def subscribe(self, path):
		if not os.path.isdir(self.BasePath + path):
			return
		self.SubscribedPaths.add(path)
