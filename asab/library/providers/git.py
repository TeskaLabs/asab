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
		pattern = re.compile(r"git\+(https?://)((.*):(.*)@)?(.*)#?(.*)?")
		path_split = pattern.findall(path)[0]
		L.debug(path_split)
		self.URLScheme, self.UserInfo, self.User, self.DeployToken, self.URLPath, self.Branch = path_split
		self.URL = "".join(path_split[:-1])  # normálně udělej self.URL jako předtím (bez branch)
		self.Branch = self.Branch if self.Branch != '' else None

		L.debug(self.URL)
		L.debug(self.Branch)

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
				try:
					os.makedirs(self.RepoPath, mode=0o700)
				except FileExistsError:
					pass

				self.GitRepository = pygit2.clone_repository(self.URL, self.RepoPath, checkout_branch=self.Branch)
			else:
				# For existing repository, pull the latest changes
				self.GitRepository = pygit2.Repository(self.RepoPath)
				self._do_pull()

		try:
			await self.ProactorService.execute(init_task)

		except KeyError as err:
			pygit_message = str(err).replace('\"', '')
			if pygit_message == "reference 'refs/remotes/origin/{}' not found".format(self.Branch):
				message = "Branch '{}' in {} does not exist.".format(self.Branch, self.URL)
			else:
				message = pygit_message
			L.exception("Error when initializing git repository: {}".format(message))
			raise SystemExit("Application is exiting.")  # NOTE: raising Exception doesn't exit the app

		except pygit2.GitError as err:
			pygit_message = str(err).replace('\"', '')
			if pygit_message == "unexpected http status code: 404":
				message = "Got status code 404: Not found. Check if the repository specified in 'providers' exist."
			elif pygit_message == "remote authentication required but no callback set":
				message = "Authentication is required. Check if the 'providers' option satisfies the format: 'git+<username>:<deploy token>@<URL>#<branch name>'"
			else:
				message = pygit_message
			L.exception("Error when initializing git repository: {}".format(message))
			raise SystemExit("Application is exiting.")

		except Exception as err:
			L.exception(err)
			raise SystemExit("Application is exiting.")

		try:
			assert self.GitRepository.remotes["origin"] is not None
		except (KeyError, AssertionError, AttributeError) as err:
			L.error("Connection to remote git repository failed: {}".format(err))
			# The library will not get ready ... maybe we can retry init_test() in a while
			return

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
