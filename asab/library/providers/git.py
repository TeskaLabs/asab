import os
import tempfile
import logging
import hashlib
import re
import typing

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

	Supports both HTTPS and SSH authentication:

	.. code::

		# HTTPS with deploy token
		[library]
		providers=git+https://<username>:<deploy token>@<url>#<branch name>

		# SSH (uses default SSH keys from ~/.ssh/)
		[library]
		providers=git+ssh://git@<url>#<branch name>

		[library:git]
		repodir=<optional location of the repository cache>
		ssh_key_path=<optional path to SSH private key, defaults to ~/.ssh/id_rsa>
		ssh_pubkey_path=<optional path to SSH public key, defaults to ~/.ssh/id_rsa.pub>
		ssh_passphrase=<optional passphrase for SSH key>
		verify_ssh_fingerprint=yes|no (default: no - auto-accepts host keys)
	"""
	def __init__(self, library, path, layer):

		# Parse URL - supports both HTTPS and SSH formats
		self._parse_url(path)
		self.Branch = self.Branch if self.Branch != '' else None


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

		super().__init__(library, self.RepoPath, layer, set_ready=False)

		self.GitRepository = None

		# Set custom SSL certificate locations if specified
		if any((Config.get("library:git", "cert_file", fallback=None), Config.get("library:git", "cert_dir", fallback=None))):
			pygit2.settings.set_ssl_cert_locations(
				cert_file=Config.get("library:git", "cert_file", fallback=None),
				cert_dir=Config.get("library:git", "cert_dir", fallback=None)
			)

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")
		self.PullLock = False

		self.SubscribedPaths = set()

		# SSH configuration
		self.SSHKeyPath = None
		self.SSHPubkeyPath = None
		self.SSHPassphrase = None
		self.VerifySSHFingerprint = False
		if self.is_ssh:
			self.SSHKeyPath = Config.get("library:git", "ssh_key_path", fallback=os.path.expanduser("~/.ssh/id_rsa"))
			self.SSHPubkeyPath = Config.get("library:git", "ssh_pubkey_path", fallback=os.path.expanduser("~/.ssh/id_rsa.pub"))
			self.SSHPassphrase = Config.get("library:git", "ssh_passphrase", fallback=None)
			self.VerifySSHFingerprint = Config.getboolean("library:git", "verify_ssh_fingerprint", fallback=False)

		self.App.TaskService.schedule(self.initialize_git_repository())
		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	def _parse_url(self, path):
		"""
		Parse git URL from various formats:
		- git+https://[user:token@]host/path[#branch]
		- git+ssh://[user@]host/path[#branch]  (e.g., git+ssh://git@github.com/user/repo.git)
		- git+git@host:path[#branch]  (SSH shorthand, e.g., git+git@github.com:user/repo.git)
		"""
		# First, try HTTPS pattern
		https_pattern = re.compile(r"git\+(https?://)((.*):(.*)@)?([^#]*)(?:#(.*))?$")
		https_match = https_pattern.match(path)

		if https_match:
			# HTTPS URL with optional credentials
			groups = https_match.groups()
			self.URLScheme = groups[0]
			self.UserInfo = groups[1] or ""
			self.User = groups[2] or ""
			self.DeployToken = groups[3] or ""
			self.URLPath = groups[4]
			self.Branch = groups[5] or ""
			self.URL = "".join([self.URLScheme, self.UserInfo, self.URLPath])
			self.is_ssh = False
			return

		# Try SSH URL pattern (git+ssh://user@host/path or git+user@host:path)
		ssh_pattern1 = re.compile(r"git\+ssh://([^@]+@)?([^/#]+)(/[^#]*)?(?:#(.*))?$")
		ssh_match1 = ssh_pattern1.match(path)

		if ssh_match1:
			# SSH URL format: git+ssh://git@github.com/user/repo.git#branch
			groups = ssh_match1.groups()
			user = groups[0] or "git@"
			host = groups[1]
			repo_path = groups[2] or ""
			self.Branch = groups[3] or ""
			self.URL = f"ssh://{user}{host}{repo_path}"
			self.URLPath = f"{host}{repo_path}"
			self.User = user.rstrip("@")
			self.DeployToken = ""
			self.URLScheme = "ssh://"
			self.UserInfo = user
			self.is_ssh = True
			return

		# Try SSH shorthand pattern: git+git@host:path
		ssh_pattern2 = re.compile(r"git\+([^@]+@)?([^:]+):([^#]+)(?:#(.*))?$")
		ssh_match2 = ssh_pattern2.match(path)

		if ssh_match2:
			# SSH shorthand format: git+git@github.com:user/repo.git#branch
			groups = ssh_match2.groups()
			user = groups[0] or "git@"
			host = groups[1]
			repo_path = groups[2]
			self.Branch = groups[3] or ""
			# Convert to full SSH URL for pygit2
			self.URL = f"{user}{host}:{repo_path}"
			self.URLPath = f"{host}:{repo_path}"
			self.User = user.rstrip("@")
			self.DeployToken = ""
			self.URLScheme = ""
			self.UserInfo = user
			self.is_ssh = True
			return

		raise ValueError(f"Invalid git URL format: {path}")


	def _create_callbacks(self):
		"""
		Create RemoteCallbacks for git operations.
		This handles SSH authentication and fingerprint verification.
		"""
		callbacks = pygit2.RemoteCallbacks()

		if self.is_ssh:
			# Set up SSH credential callback
			def credentials_cb(url, username_from_url, allowed_types):
				L.debug("Git SSH authentication requested", struct_data={
					"url": url,
					"username": username_from_url,
					"allowed_types": allowed_types
				})

				# Check if SSH key authentication is allowed
				if allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
					# Expand paths
					key_path = os.path.expanduser(self.SSHKeyPath)
					pubkey_path = os.path.expanduser(self.SSHPubkeyPath)

					# Check if key files exist
					if not os.path.exists(key_path):
						L.error(f"SSH private key not found: {key_path}")
						return None
					if not os.path.exists(pubkey_path):
						L.warning(f"SSH public key not found: {pubkey_path}, trying without it")
						pubkey_path = ""

					L.debug(f"Using SSH key: {key_path}")

					try:
						return pygit2.Keypair(
							username_from_url or self.User or "git",
							pubkey_path,
							key_path,
							self.SSHPassphrase or ""
						)
					except Exception as e:
						L.error(f"Failed to create SSH keypair: {e}")
						return None

				return None

			callbacks.credentials = credentials_cb

			# Set up certificate/fingerprint callback
			# This prevents hanging on "Are you sure you want to continue connecting?" prompt
			def certificate_check_cb(cert, valid, host):
				if self.VerifySSHFingerprint:
					# TODO: Could implement proper known_hosts verification here
					L.warning(
						"SSH fingerprint verification is enabled but not yet fully implemented. "
						"Accepting host key.",
						struct_data={"host": host}
					)
				else:
					L.debug(f"Auto-accepting SSH host key for {host}")
				# Return True to accept the certificate
				return True

			callbacks.certificate_check = certificate_check_cb

		return callbacks


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
		except pygit2.GitError as err:
			L.warning(
				"Periodic pull from the remote repository failed: {}".format(err),
				struct_data={"url": self.URLPath}
			)
		finally:
			self.PullLock = False


	async def initialize_git_repository(self):

		def init_task():
			if pygit2.discover_repository(self.RepoPath) is None:
				# For a new repository, clone the remote bit
				os.makedirs(self.RepoPath, mode=0o700, exist_ok=True)
				try:
					callbacks = self._create_callbacks()
					self.GitRepository = pygit2.clone_repository(
						url=self.URL,
						path=self.RepoPath,
						checkout_branch=self.Branch,
						callbacks=callbacks
					)
				except Exception as err:
					L.exception("Error when cloning git repository: {}".format(err))
			else:
				# For existing repository, pull the latest changes
				self.GitRepository = pygit2.Repository(self.RepoPath)
				self._do_pull()

		try:
			await self.ProactorService.execute(init_task)

		except KeyError as err:
			pygit_message = str(err).replace('\"', '')
			if "'refs/remotes/origin/{}'".format(self.Branch) in pygit_message:
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
			if "unexpected http status code: 404" in pygit_message:
				# repository not found
				L.exception(
					"Git repository not found.",
					struct_data={
						"url": self.URLPath
					}
				)
			elif "remote authentication required but no callback set" in pygit_message:
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
			elif 'cannot redirect from' in pygit_message:
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

		assert hasattr(self.GitRepository, "remotes"), "Git repository not initialized."
		assert self.GitRepository.remotes["origin"] is not None, "Git repository not initialized."
		await self._set_ready()


	def _do_fetch(self):
		"""
		It fetches the remote repository and returns the commit ID of the remote branch

		:return: The commit id of the latest commit on the remote repository.
		"""
		if self.GitRepository is None:
			return None

		callbacks = self._create_callbacks()
		self.GitRepository.remotes["origin"].fetch(callbacks=callbacks)
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


	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		self.SubscribedPaths.add(path)
