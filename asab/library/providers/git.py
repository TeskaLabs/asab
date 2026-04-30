import asyncio
import os
import tempfile
import logging
import hashlib
import re
import typing

from .filesystem import FileSystemLibraryProvider
from ...config import Config
from ...utils import convert_to_seconds

#

L = logging.getLogger(__name__)

#

try:
	import pygit2
except ImportError:
	L.critical("Please install pygit2 package to enable Git Library Provider. >>> pip install pygit2")
	raise SystemExit("Application exiting... .")

# Try to get the SSH key credential type constant - location varies by pygit2 version
try:
	GIT_CREDTYPE_SSH_KEY = pygit2.GIT_CREDTYPE_SSH_KEY
except AttributeError:
	try:
		GIT_CREDTYPE_SSH_KEY = pygit2.credentials.GIT_CREDTYPE_SSH_KEY
	except (AttributeError, ImportError):
		try:
			GIT_CREDTYPE_SSH_KEY = pygit2.GIT_CREDENTIAL_SSH_KEY
		except AttributeError:
			try:
				GIT_CREDTYPE_SSH_KEY = pygit2.credentials.GIT_CREDENTIAL_SSH_KEY
			except (AttributeError, ImportError):
				# Fall back to the numeric value if constant not found
				GIT_CREDTYPE_SSH_KEY = 2  # Standard value across libgit2 versions


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
		# optional pull interval: fragment may be ``<branch>#pull=10h``
		# interval shorter than 1 minute defaults to 1 minute
		providers=git+https://<username>:<deploy token>@<url>#main#pull=10h

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

		# Initialize attributes to avoid attribute errors
		self.URLScheme = ""
		self.UserInfo = ""
		self.User = ""
		self.DeployToken = ""
		self.URLPath = ""
		self.Branch = ""
		self.URL = ""
		self.UsesSSH = False
		self.GitRepository: typing.Optional[pygit2.Repository] = None
		self.LastPull = None
		self.PullInterval = 43200  # default 12 h; overridden by ``#pull=`` in URL fragment

		# Parse URL - supports both HTTPS and SSH formats
		self._parse_url(path)
		self.Branch = self.Branch if self.Branch != "" else None  # pygit2 expects None for default branch

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

		# Set custom SSL certificate locations if specified
		cert_file = Config.get("library:git", "cert_file", fallback=None)
		cert_dir = Config.get("library:git", "cert_dir", fallback=None)
		if (cert_file is not None) or (cert_dir is not None):
			pygit2.settings.set_ssl_cert_locations(cert_file=cert_file, cert_dir=cert_dir)

		from ...proactor import Module
		self.App.add_module(Module)
		self.ProactorService = self.App.get_service("asab.ProactorService")
		self.PullLock = asyncio.Lock()

		self.SubscribedPaths = set()

		# SSH configuration
		self.SSHKeyPath = None
		self.SSHPubkeyPath = None
		self.SSHPassphrase = None
		self.VerifySSHFingerprint = False
		if self.UsesSSH:
			self.SSHKeyPath = Config.get("library:git", "ssh_key_path", fallback=os.path.expanduser("~/.ssh/id_rsa"))
			self.SSHPubkeyPath = Config.get("library:git", "ssh_pubkey_path", fallback=os.path.expanduser("~/.ssh/id_rsa.pub"))
			self.SSHPassphrase = Config.get("library:git", "ssh_passphrase", fallback=None)
			self.VerifySSHFingerprint = Config.getboolean("library:git", "verify_ssh_fingerprint", fallback=False)

		self.App.TaskService.schedule(self.initialize_git_repository())

		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_check)


	def _parse_url_fragment(self, fragment):
		"""
		Parse the URL fragment for checkout branch and optional ``pull=`` interval.

		There is only one ``#`` in a URL; further ``#`` appear inside the fragment
		(e.g. ``#main#pull=10h``), matching the libsreg provider convention.

		:return: ``(branch, pull_interval)`` where ``pull_interval`` is the raw value
			after ``pull=``, or ``None`` if absent.
		"""
		branch = ""
		pull_interval = None
		if fragment:
			for part in fragment.split("#"):
				if part.startswith("pull="):
					pull_interval = part[5:]
				elif "=" not in part:
					branch = part
		return branch, pull_interval


	def _parse_url(self, path):
		"""
		Parse git URL from various formats:
		- git+https://[user:token@]host/path[#branch[#pull=<interval>]]
		- git+ssh://[user@]host/path[#branch[#pull=<interval>]]  (e.g., git+ssh://git@github.com/user/repo.git)
		- git+git@host:path[#branch[#pull=<interval>]]  (SSH shorthand, e.g., git+git@github.com:user/repo.git)

		Full example (branch ``main``, pull interval 10 hours; only one ``#`` starts the URL fragment,
		the second ``#`` separates ``main`` and ``pull=10h`` inside that fragment)::

			git+https://deploy:token@git.example.com/org/repo.git#main#pull=10h

		That yields clone URL ``https://deploy:token@git.example.com/org/repo.git``, branch ``main``,
		and ``pull=10h`` is applied to ``PullInterval`` (not part of the clone URL).
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
			self.Branch, pull_interval = self._parse_url_fragment(groups[5] or "")
			if pull_interval is not None:
				self.PullInterval = convert_to_seconds(pull_interval)
			self.URL = "".join([self.URLScheme, self.UserInfo, self.URLPath])
			self.UsesSSH = False
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
			self.Branch, pull_interval = self._parse_url_fragment(groups[3] or "")
			if pull_interval is not None:
				self.PullInterval = convert_to_seconds(pull_interval)
			self.URL = "ssh://{}{}{}".format(user, host, repo_path)
			self.URLPath = "{}{}".format(host, repo_path)
			self.User = user.rstrip("@")
			self.DeployToken = ""
			self.URLScheme = "ssh://"
			self.UserInfo = user
			self.UsesSSH = True
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
			self.Branch, pull_interval = self._parse_url_fragment(groups[3] or "")
			if pull_interval is not None:
				self.PullInterval = convert_to_seconds(pull_interval)
			# Convert to full SSH URL for pygit2
			self.URL = "{}{}:{}".format(user, host, repo_path)
			self.URLPath = "{}:{}".format(host, repo_path)
			self.User = user.rstrip("@")
			self.DeployToken = ""
			self.URLScheme = ""
			self.UserInfo = user
			self.UsesSSH = True
			return

		raise ValueError("Invalid git URL format: {}".format(path))


	def _create_callbacks(self):
		"""
		Create RemoteCallbacks for git operations.
		This handles SSH authentication and fingerprint verification.
		"""
		callbacks = pygit2.RemoteCallbacks()

		if self.UsesSSH:
			# Set up SSH credential callback
			def credentials_cb(url, username_from_url, allowed_types):
				L.debug(
					"Git SSH credentials requested",
					struct_data={
						"layer": self.Layer,
						"url": url,
						"username": username_from_url,
						"allowed_types": allowed_types
					}
				)

				# Warn if the allowed_types doesn't match what we expect
				if not (allowed_types & GIT_CREDTYPE_SSH_KEY):
					L.warning(
						"SSH credentials requested but allowed_types ({}) ".format(allowed_types)
						+ "doesn't include SSH_KEY flag ({}). Attempting anyway.".format(GIT_CREDTYPE_SSH_KEY),
						struct_data={
							"layer": self.Layer,
							"url": url,
						}
					)

				# Expand paths
				key_path = os.path.expanduser(self.SSHKeyPath)
				pubkey_path = os.path.expanduser(self.SSHPubkeyPath)

				# Check if key files exist
				if not os.path.exists(key_path):
					L.error(
						"SSH private key not found",
						struct_data={"layer": self.Layer, "path": key_path}
					)
					return None
				if not os.path.exists(pubkey_path):
					L.warning(
						"SSH public key not found",
						struct_data={"layer": self.Layer, "path": pubkey_path}
					)
					pubkey_path = ""

				L.debug("Using SSH key", struct_data={"layer": self.Layer, "path": key_path})

				try:
					return pygit2.Keypair(
						username_from_url or self.User or "git",
						pubkey_path,
						key_path,
						self.SSHPassphrase or ""
					)
				except Exception as e:
					L.exception(
						"Failed to create SSH key-pair",
						struct_data={"layer": self.Layer, "path": key_path, "error": str(e)}
					)
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
						struct_data={"layer": self.Layer, "host": host}
					)
				else:
					L.debug(
						"Auto-accepting SSH host key",
						struct_data={"layer": self.Layer, "host": host}
					)
				# Return True to accept the certificate
				return True

			callbacks.certificate_check = certificate_check_cb

		return callbacks


	async def _periodic_check(self, event_name):
		"""
		Periodic check that runs every 60 seconds.
		If the git repository is not initialized, attempts to initialize it.
		If initialized and PullInterval has passed, performs a pull.
		"""
		if self.GitRepository is None:
			# Repository not initialized yet - try to init. Retry happens on next tick (60s).
			self.App.TaskService.schedule(self.initialize_git_repository())
			return

		if self.PullLock.locked():
			return

		if self.LastPull is not None and self.App.time() - self.LastPull < self.PullInterval:
			# Do not pull if the last pull was done less than PullInterval ago
			return

		await self._periodic_pull()


	async def _periodic_pull(self):
		"""
		Perform the actual pull from the remote repository.
		This should only be called when all conditions are met (initialized, not locked, interval passed).
		"""
		async with self.PullLock:
			try:
				to_publish = await self.ProactorService.execute(self._do_pull)
				self.LastPull = self.App.time()
				# Once reset of the head is finished, PubSub message about the change in the subscribed directory gets published.
				for path in to_publish:
					self.App.PubSub.publish("Library.change!", self, path)
			except pygit2.GitError as err:
				L.exception(
					"Periodic pull from the remote repository failed: {}".format(err),
					struct_data={"layer": self.Layer, "url": self.URLPath}
				)


	def _init_task(self):
		"""
		The actual git repository initialization task.
		This is the core logic without any retry handling.
		This is a synchronous method that runs in the proactor thread.
		Only clones/opens the repository - does NOT pull (that's handled by _periodic_pull).
		"""
		if pygit2.discover_repository(self.RepoPath) is None:
			# For a new repository, clone the remote bit
			os.makedirs(self.RepoPath, mode=0o700, exist_ok=True)
			callbacks = self._create_callbacks()
			self.GitRepository = pygit2.clone_repository(
				url=self.URL,
				path=self.RepoPath,
				checkout_branch=self.Branch,
				callbacks=callbacks
			)
		else:
			# For existing repository, pull the latest changes
			self.GitRepository = pygit2.Repository(self.RepoPath)
			self._do_pull()

		# Verify the repository is valid
		if not hasattr(self.GitRepository, "remotes"):
			raise RuntimeError("Git repository object is in an invalid state (missing remote configuration)")


	async def initialize_git_repository(self):
		"""
		Initialize git repository by cloning or pulling latest changes.
		This is a single attempt without retries. Callers should handle retries if needed.
		On failure, logs the error but does not retry.
		All exceptions are caught and logged to prevent unhandled exceptions in scheduled tasks.
		"""
		try:
			try:
				await self.ProactorService.execute(self._init_task)
			except KeyError as err:
				pygit_message = str(err).replace('\"', '')
				if "'refs/remotes/origin/{}'".format(self.Branch) in pygit_message:
					L.exception(
						"Branch does not exist.",
						struct_data={"url": self.URLPath, "branch": self.Branch}
					)
				else:
					L.exception(
						"Error when initializing git repository",
						struct_data={"layer": self.Layer, "error": pygit_message}
					)
				return
			except pygit2.GitError as err:
				pygit_message = str(err).replace('\"', '')
				if "unexpected http status code: 404" in pygit_message:
					L.exception("Git repository not found.", struct_data={"layer": self.Layer, "url": self.URLPath})
				elif "remote authentication required but no callback set" in pygit_message:
					L.exception(
						"Authentication failed when initializing git repository.\n"
						"Check if the 'providers' option satisfies the format: 'git+<username>:<deploy token>@<URL>#<branch name>'",
						struct_data={"layer": self.Layer, "url": self.URLPath, "username": self.User, "deploy_token": self.DeployToken}
					)
				elif 'cannot redirect from' in pygit_message:
					L.exception("Git repository not found.", struct_data={"layer": self.Layer, "url": self.URLPath})
				elif 'Temporary failure in name resolution' in pygit_message:
					L.exception(
						"Git repository not initialized: connection failed. Check your network connection.",
						struct_data={"layer": self.Layer, "url": self.URLPath}
					)
				else:
					L.exception(
						"Git repository not initialized",
						struct_data={"layer": self.Layer, "error": str(err)}
					)
				return
			except RuntimeError as err:
				L.error(
					"Git repository not initialized: {}".format(str(err)),
					struct_data={"layer": self.Layer, "url": self.URLPath}
				)
				return
			except Exception as err:
				L.exception(
					"Git repository not initialized",
					struct_data={"layer": self.Layer, "error": str(err)}
				)
				return

			# If everything went fine, set the provider as ready
			await self._set_ready()

		except Exception as err:
			# Catch-all for any unexpected errors (e.g., in _set_ready)
			L.exception(
				"Unexpected error during git repository initialization",
				struct_data={"layer": self.Layer, "url": self.URLPath, "error": str(err)}
			)


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

		# Before new head is set, check the diffs.
		# If changes in subscribed directory occurred, add path to "to_publish" list.
		to_publish = []
		for path in self.SubscribedPaths:
			for i in self.GitRepository.diff(self.GitRepository.head.target, new_commit_id).deltas:
				if ("/" + i.old_file.path).startswith(path):
					to_publish.append(path)

		# Reset HEAD
		self.GitRepository.head.set_target(new_commit_id)
		self.GitRepository.reset(new_commit_id, pygit2.GIT_RESET_HARD)

		L.info("Pulled repository", struct_data={"layer": self.Layer, "url": self.URLPath, "commit_id": new_commit_id})
		return to_publish


	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		self.SubscribedPaths.add(path)
