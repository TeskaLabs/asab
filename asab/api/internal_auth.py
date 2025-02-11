import typing
import logging
import datetime
import json
import os

try:
	# Optional dependency for using internal authorization
	import jwcrypto
	import jwcrypto.jwt
	import jwcrypto.jwk
except ModuleNotFoundError:
	jwcrypto = None

from ..contextvars import Authz


L = logging.getLogger(__name__)


class InternalAuth:
	"""
	Internal authorization component that enables authorized communication between ASAB services.
	It manages shared private key in Zookeeper and issues ID tokens for superuser access.
	"""

	def __init__(self, app, zkc):
		self.App = app
		self.ZooKeeperContainer = zkc
		self.AuthService = None

		# Private key is prerequisite to issuing ID tokens and making authorized requests
		self.PrivateKeyPath = "/asab/auth/internal_auth_private.key"
		self.PrivateKey = None
		self.IdToken = None
		self.IdTokenExpiration: datetime.timedelta = datetime.timedelta(seconds=30 * 60)

		# Public key is necessary for verifying ID tokens and accepting authorized requests
		self.PublicKeyProvider = None

		self.App.PubSub.subscribe("Application.tick/300!", self._every_5_minutes)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)


	async def initialize(self, app):
		"""
		Initialize the internal authorization: Prepare the key pair and issue the first ID token.

		Args:
			app: ASAB application instance
		"""
		self.AuthService = self.App.get_service("asab.AuthService")
		if self.AuthService is not None:
			auth_provider = self.AuthService.get_provider("id_token")
			assert auth_provider is not None

			from ..web.auth.providers.key_providers import DirectPublicKeyProvider
			self.PublicKeyProvider = DirectPublicKeyProvider(self.App)
			auth_provider.add_key_provider(self.PublicKeyProvider)

		task_service = self.App.get_service("asab.TaskService")
		task_service.schedule(self._prepare_keys_and_tokens())


	def obtain_bearer_token(self) -> str:
		"""
		Obtain a Bearer token for internal authorized communication.

		Returns:
			Bearer token string.
		"""
		if jwcrypto is None:
			raise ModuleNotFoundError(
				"You are trying to use internal auth without 'jwcrypto' installed. "
				"Please run 'pip install jwcrypto' or install asab with 'authz' optional dependency."
			)

		authz = Authz.get(None)
		if authz is not None:
			L.warning(
				"Using internal (superuser) authorization in an already authorized context. "
				"This is potentially unwanted and dangerous.",
			)

		if not self._is_id_token_ready():
			self._issue_id_token()

		return "Bearer {}".format(self.IdToken.serialize())


	async def _prepare_keys_and_tokens(self):
		if jwcrypto is None:
			return

		await self._ensure_private_key()

		if not self._is_id_token_ready(required_leeway=300):
			self._issue_id_token()

		if self.PublicKeyProvider is not None:
			self._update_public_key()


	async def _every_5_minutes(self, msg):
		task_service = self.App.get_service("asab.TaskService")
		task_service.schedule(self._prepare_keys_and_tokens())


	def _on_zk_ready(self, msg, zkc):
		task_service = self.App.get_service("asab.TaskService")
		task_service.schedule(self._prepare_keys_and_tokens())


	async def _ensure_private_key(self):
		private_key_json = None
		# Attempt to create and write a new private key
		# while avoiding race condition with other ASAB services
		while not private_key_json:
			# Try to get the key
			try:
				private_key_json, _ = self.ZooKeeperContainer.ZooKeeper.Client.get(self.PrivateKeyPath)
				break
			except kazoo.exceptions.NoNodeError:
				pass

			# Generate a new key
			private_key = jwcrypto.jwk.JWK.generate(kty="EC", crv="P-256")
			private_key_json = json.dumps(private_key.export(as_dict=True)).encode("utf-8")
			try:
				self.ZooKeeperContainer.ZooKeeper.Client.create(self.PrivateKeyPath, private_key_json, makepath=True)
				L.info("Internal auth key created.", struct_data={
					"kid": private_key.key_id, "path": self.PrivateKeyPath})
			except kazoo.exceptions.NodeExistsError:
				# Another ASAB service has probably created the key in the meantime
				pass

		private_key = jwcrypto.jwk.JWK.from_json(private_key_json)
		if private_key != self.PrivateKey:
			# Private key has changed
			self.PrivateKey = private_key
			L.debug("Private key updated.", struct_data={"kid": private_key.key_id})
			self.IdToken = None

		assert self.PrivateKey is not None


	def _is_id_token_ready(self, required_leeway: int = 0):
		"""
		Check if the current ID token is valid and does not expire soon.

		Args:
			required_leeway: Minimum number of seconds the token must be valid for from now.
		"""
		if self.IdToken is None:
			return False

		# Check expiration
		claims = json.loads(self.IdToken.claims)
		exp = claims.get("exp")
		if (
			datetime.datetime.now(datetime.timezone.utc)
			+ datetime.timedelta(seconds=required_leeway)
		).timestamp() > exp:
			# Token expired or will expire soon
			return False

		return True


	def _issue_id_token(self):
		if self.PrivateKey is None:
			raise RuntimeError("Private key is not initialized.")

		# Issue a new ID token
		claims = self._build_auth_claims()
		self.IdToken = jwcrypto.jwt.JWT(
			header={
				"alg": "ES256",
				"typ": "JWT",
				"kid": self.PrivateKey.key_id,
			},
			claims=json.dumps(claims)
		)
		self.IdToken.make_signed_token(self.PrivateKey)
		L.info("New internal auth token issued.", struct_data={"exp": claims.get("exp")})


	def _update_public_key(self):
		public_key = self.PrivateKey.public()
		self.PublicKeyProvider.set_public_key(public_key)
		L.debug("Public key updated.", struct_data={"kid": public_key.key_id})


	def _get_own_discovery_url(self):
		instance_id = os.getenv("INSTANCE_ID", None)
		if instance_id:
			return "http://{}.instance_id.asab".format(instance_id)

		service_id = os.getenv("SERVICE_ID", None)
		if service_id:
			return "http://{}.service_id.asab".format(service_id)

		return "http://{}".format(self.App.HostName)


	def _build_auth_claims(self):
		# Use this service's discovery URL as issuer ID and authorized party ID
		my_discovery_url = self._get_own_discovery_url()
		expiration = datetime.datetime.now(datetime.timezone.utc) + self.IdTokenExpiration
		return {
			# Issuer (URL of the app that created the token)
			"iss": my_discovery_url,
			# Issued at
			"iat": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
			# Expires at
			"exp": int((expiration).timestamp()),
			# Authorized party
			"azp": my_discovery_url,
			# Audience (who is allowed to use this token)
			"aud": "http://{}".format(self.App.HostName),  # TODO: Something that signifies "anyone in this internal space"
			# Tenants and resources
			"resources": {
				"*": ["authz:superuser"],
			}
		}
