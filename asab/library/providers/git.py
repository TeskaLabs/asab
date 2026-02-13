import asyncio
import os
import tempfile
import logging
import hashlib
import re
import typing
import time

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

		# SSH (uses default SSH keys from ~/.ssh/)
		[library]
		providers=git+ssh://git@<url>#<branch name>

		[library:git]
		repodir=<optional location of the repository cache>
		ssh_key_path=<optional path to SSH private key, defaults to ~/.ssh/id_rsa>
		ssh_pubkey_path=<optional path to SSH public key, defaults to ~/.ssh/id_rsa.pub>
		ssh_passphrase=<optional passphrase for SSH key>
		verify_ssh_fingerprint=yes|no (default: no - auto-accepts host keys)
		server_timeout=<timeout in seconds for git server operations, default: 30>
		max_retries=<number of retry attempts for transient errors, default: 3>
		retry_delay=<initial delay in seconds between retries, default: 2>
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

		# Retry configuration for transient errors
		self.MaxRetries = Config.getint("library:git", "max_retries", fallback=3)
		self.RetryDelay = Config.getint("library:git", "retry_delay", fallback=2)
		
		# Timeout configuration (in seconds)
		self.ServerTimeout = Config.getint("library:git", "server_timeout", fallback=30)
		
		# Set pygit2 server timeout
		self._configure_timeout()

		self.App.TaskService.schedule(self.initialize_git_repository())

		self.App.PubSub.subscribe("Application.tick/60!", self._periodic_pull)


	def _configure_timeout(self):
		"""Configure pygit2/libgit2 server timeout."""
		try:
			# Try different pygit2 API versions for setting timeout
			timeout_ms = self.ServerTimeout * 1000  # Convert to milliseconds
			
			# Try pygit2.Settings (newer API)
			if hasattr(pygit2, 'Settings'):
				if hasattr(pygit2.Settings, 'server_timeout'):
					pygit2.Settings.server_timeout = timeout_ms
					L.info(
						"🐰 ⏱️ Set server timeout via pygit2.Settings: {}ms ({}s)".format(timeout_ms, self.ServerTimeout),
						struct_data={"layer": self.Layer, "timeout_ms": timeout_ms, "timeout_seconds": self.ServerTimeout}
					)
					return
			
			# Try pygit2.settings (older API)
			if hasattr(pygit2, 'settings'):
				if hasattr(pygit2.settings, 'server_timeout'):
					pygit2.settings.server_timeout = timeout_ms
					L.info(
						"🐰 ⏱️ Set server timeout via pygit2.settings: {}ms ({}s)".format(timeout_ms, self.ServerTimeout),
						struct_data={"layer": self.Layer, "timeout_ms": timeout_ms, "timeout_seconds": self.ServerTimeout}
					)
					return
			
			# Try pygit2.option (another API variant)
			if hasattr(pygit2, 'option'):
				# GIT_OPT_SET_SERVER_CONNECT_TIMEOUT = 37 (from libgit2)
				try:
					pygit2.option(37, timeout_ms)
					L.info(
						"🐰 ⏱️ Set server timeout via pygit2.option: {}ms ({}s)".format(timeout_ms, self.ServerTimeout),
						struct_data={"layer": self.Layer, "timeout_ms": timeout_ms, "timeout_seconds": self.ServerTimeout}
					)
					return
				except:
					pass
			
			L.warning(
				"🐰 ⚠️ Could not set server timeout - API not available in pygit2 version {}. Using system defaults.".format(pygit2.__version__),
				struct_data={"layer": self.Layer, "pygit2_version": pygit2.__version__}
			)
			
		except Exception as e:
			L.warning(
				"🐰 ⚠️ Failed to set server timeout: {}".format(str(e)),
				struct_data={"layer": self.Layer, "error": str(e)}
			)

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
			self.Branch = groups[3] or ""
			self.URL = f"ssh://{user}{host}{repo_path}"
			self.URLPath = f"{host}{repo_path}"
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
			self.Branch = groups[3] or ""
			# Convert to full SSH URL for pygit2
			self.URL = f"{user}{host}:{repo_path}"
			self.URLPath = f"{host}:{repo_path}"
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
					error_msg = "SSH private key not found at: {}".format(key_path)
					L.error(error_msg, struct_data={"layer": self.Layer, "path": key_path})
					raise FileNotFoundError(error_msg)
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
					# Re-raise instead of returning None - pygit2 requires valid credential or exception
					raise

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


	async def _periodic_pull(self, event_name):
		"""
		Changes in remote repository are being pulled every minute. `PullLock` flag ensures that only if previous "pull" has finished, new one can start.
		"""
		if self.PullLock.locked():
			return

		async with self.PullLock:
			if self.GitRepository is None:
				self.App.TaskService.schedule(self.initialize_git_repository())
				return

			try:
				to_publish = await self.ProactorService.execute(self._do_pull)
				# Once reset of the head is finished, PubSub message about the change in the subscribed directory gets published.
				for path in to_publish:
					self.App.PubSub.publish("Library.change!", self, path)
			except pygit2.GitError as err:
				L.exception(
					"Periodic pull from the remote repository failed: {}".format(err),
					struct_data={"layer": self.Layer, "url": self.URLPath}
				)


	def _is_transient_error(self, error_msg):
		"""Check if error is transient and should be retried."""
		transient_patterns = [
			"Failed to retrieve list of SSH authentication methods",
			"Failed getting response",
			"Connection refused",
			"Connection reset",
			"Connection timed out",
			"Network is unreachable",
		]
		error_str = str(error_msg).lower()
		return any(pattern.lower() in error_str for pattern in transient_patterns)

	async def initialize_git_repository(self):
		"""
		Initialize git repository by cloning or pulling latest changes.
		"""
		init_start = time.time()
		L.info("🐰 Initializing git repository", struct_data={"layer": self.Layer, "url": self.URLPath})

		def init_task():

			if pygit2.discover_repository(self.RepoPath) is None:
				# For a new repository, clone the remote bit
				os.makedirs(self.RepoPath, mode=0o700, exist_ok=True)
				
				# Retry clone on transient errors
				last_error = None
				for attempt in range(self.MaxRetries):
					try:
						if attempt > 0:
							delay = self.RetryDelay * (attempt + 1)
							L.info("🐰 Retry attempt {} after {}s".format(attempt + 1, delay))
							time.sleep(delay)
						
						L.info("🐰 Cloning repository (attempt {}/{})".format(attempt + 1, self.MaxRetries), struct_data={"layer": self.Layer, "url": self.URL})
						clone_start = time.time()
						
						callbacks = self._create_callbacks()
						self.GitRepository = pygit2.clone_repository(
							url=self.URL,
							path=self.RepoPath,
							checkout_branch=self.Branch,
							callbacks=callbacks
						)
						
						clone_duration_ms = (time.time() - clone_start) * 1000
						L.info(
							"🐰 Clone completed in {:.1f}ms".format(clone_duration_ms),
							struct_data={"layer": self.Layer, "duration_ms": round(clone_duration_ms, 1)}
						)
						break  # Success!
						
					except pygit2.GitError as e:
						last_error = e
						if self._is_transient_error(str(e)):
							L.warning("🐰 Transient error: {}".format(str(e)))
							if attempt + 1 < self.MaxRetries:
								continue  # Retry
						# Non-transient or last attempt - raise
						raise
				
				if last_error and attempt + 1 >= self.MaxRetries:
					L.error("🐰 Clone failed after {} attempts".format(self.MaxRetries))
					raise last_error

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
				L.exception(
					"Error when initializing git repository",
					struct_data={"layer": self.Layer, "error": pygit_message}
				)

			return

		except pygit2.GitError as err:
			pygit_message = str(err).replace('\"', '')
			if "unexpected http status code: 404" in pygit_message:
				# repository not found
				L.exception("Git repository not found.", struct_data={"layer": self.Layer, "url": self.URLPath})
			elif "remote authentication required but no callback set" in pygit_message:
				# either repository not found or authentication failed
				L.exception(
					"Authentication failed when initializing git repository.\n"
					"Check if the 'providers' option satisfies the format: 'git+<username>:<deploy token>@<URL>#<branch name>'",
					struct_data={
						"layer": self.Layer,
						"url": self.URLPath,
						"username": self.User,
						"deploy_token": self.DeployToken
					}
				)
			elif 'cannot redirect from' in pygit_message:
				# bad URL
				L.exception(
					"Git repository not found.",
					struct_data={"layer": self.Layer, "url": self.URLPath}
				)
			elif 'Temporary failure in name resolution' in pygit_message:
				# Internet connection does not work
				L.exception(
					"Git repository not initialized: connection failed. Check your network connection.",
					struct_data={
						"layer": self.Layer,
						"url": self.URLPath
					}
				)
			else:
				L.exception(
					"Git repository not initialized",
					struct_data={"layer": self.Layer, "error": str(err)}
				)

			return

		except Exception as err:
			L.exception(
				"Git repository not initialized",
				struct_data={"layer": self.Layer, "error": str(err)}
			)
			return

		if not hasattr(self.GitRepository, "remotes"):
			L.error(
				"Git repository not initialized: Git repository object is in an invalid state (missing remote configuration)",
				struct_data={"layer": self.Layer, "url": self.URLPath}
			)
			return

		if "origin" not in self.GitRepository.remotes.names():
			L.error(
				"Git repository not initialized: origin remote missing",
				struct_data={"layer": self.Layer, "url": self.URLPath}
			)
			return

		# If everything went fine, set the provider as ready
		await self._set_ready()
		
		init_duration_ms = (time.time() - init_start) * 1000
		L.info(
			"🐰 ✅ Git repository initialized successfully in {:.1f}ms".format(init_duration_ms),
			struct_data={"layer": self.Layer, "total_duration_ms": round(init_duration_ms, 1)}
		)


	def _do_fetch(self):
		"""
		It fetches the remote repository and returns the commit ID of the remote branch

		:return: The commit id of the latest commit on the remote repository.
		"""
		if self.GitRepository is None:
			return None

		# Retry fetch on transient errors
		last_error = None
		for attempt in range(self.MaxRetries):
			try:
				if attempt > 0:
					delay = self.RetryDelay * (attempt + 1)
					L.info("🐰 Retry fetch attempt {} after {}s".format(attempt + 1, delay))
					time.sleep(delay)
				
				fetch_start = time.time()
				L.info("🐰 Fetching from remote (attempt {}/{})".format(attempt + 1, self.MaxRetries), struct_data={"layer": self.Layer})
				
				callbacks = self._create_callbacks()
				self.GitRepository.remotes["origin"].fetch(callbacks=callbacks)
				
				fetch_duration_ms = (time.time() - fetch_start) * 1000
				L.info("🐰 Fetch completed in {:.1f}ms".format(fetch_duration_ms), struct_data={"layer": self.Layer, "duration_ms": round(fetch_duration_ms, 1)})
				
				if self.Branch is None:
					reference = self.GitRepository.lookup_reference("refs/remotes/origin/HEAD")
				else:
					reference = self.GitRepository.lookup_reference("refs/remotes/origin/{}".format(self.Branch))
				commit_id = reference.peel().id
				return commit_id
				
			except pygit2.GitError as e:
				last_error = e
				if self._is_transient_error(str(e)):
					L.warning("🐰 Transient fetch error: {}".format(str(e)))
					if attempt + 1 < self.MaxRetries:
						continue  # Retry
				# Non-transient or last attempt - raise
				L.error("🐰 Fetch failed after {} attempts".format(attempt + 1))
				raise
		
		if last_error:
			raise last_error


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

		return to_publish


	async def subscribe(self, path, target: typing.Union[str, tuple, None] = None):
		self.SubscribedPaths.add(path)
