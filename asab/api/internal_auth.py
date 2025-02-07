import typing
import logging
try:
	# Optional dependency for using internal authorization
	import jwcrypto
	import jwcrypto.jwt
	import jwcrypto.jwk
except ModuleNotFoundError:
	jwcrypto = None

from ..web.auth.providers.key_providers import DirectPublicKeyProvider
from ....contextvars import Authz


L = logging.getLogger(__name__)


class InternalAuth:
	def __init__(self, app):
		self.App = app

		self.PrivateKeyPath = "/asab/auth/internal_auth_private.key"
		self.PrivateKey = None
		self.PublicKeyProvider = None
		self.IdToken = None
		self.IdTokenExpiration: datetime.timedelta = datetime.timedelta(seconds=30 * 60)

		self.App.PubSub.subscribe("Application.tick/300!", self._on_tick)
		self.App.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_ready)


	async def initialize(self, app):
		auth_service = self.App.get_service("asab.AuthService")
		if auth_service is None:
			return
		auth_provider = auth_service.get_provider("id_token")
		assert auth_provider is not None
		self.PublicKeyProvider = auth_service.create_public_key_provider(type="direct")


	def obtain_bearer_token(self):
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

		return "Bearer {}".format(self.IdToken.serialize())


	def _on_tick(self, msg):
		if jwcrypto is not None:
			self._ensure_id_token()


	def _on_zk_ready(self, msg, zkc):
		task_service = self.App.get_service("asab.TaskService")
		if zkc == self.ZooKeeperContainer:
			if jwcrypto is not None:
				task_service.schedule(self._ensure_private_key(zkc))


	async def _ensure_private_key(self, zkc=None):
		zkc = zkc or self.ZooKeeperContainer
		private_key_json = None
		# Attempt to create and write a new private key
		# while avoiding race condition with other ASAB services
		while not private_key_json:
			# Try to get the key
			try:
				private_key_json, _ = zkc.ZooKeeper.Client.get(self.PrivateKeyPath)
				break
			except kazoo.exceptions.NoNodeError:
				pass

			# Generate a new key
			private_key = jwcrypto.jwk.JWK.generate(kty="EC", crv="P-256")
			private_key_json = json.dumps(private_key.export(as_dict=True)).encode("utf-8")
			try:
				zkc.ZooKeeper.Client.create(self.PrivateKeyPath, private_key_json, makepath=True)
				L.info("Internal auth key created.", struct_data={
					"kid": private_key.key_id, "path": self.PrivateKeyPath})
			except kazoo.exceptions.NodeExistsError:
				# Another ASAB service has probably created the key in the meantime
				pass

		private_key = jwcrypto.jwk.JWK.from_json(private_key_json)
		if private_key != self.PrivateKey:
			# Private key has changed
			self.PrivateKey = private_key
			self._update_public_key()
			self._ensure_id_token(force_new=True)


	def _ensure_id_token(self, force_new: bool = False):
		assert self.PrivateKey

		if self.IdToken and not force_new:
			claims = json.loads(self.IdToken.claims)
			if claims.get("exp") > (
				datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=300)
			).timestamp():
				# Token is valid and does not expire soon
				return

		self.IdToken = jwcrypto.jwt.JWT(
			header={
				"alg": "ES256",
				"typ": "JWT",
				"kid": self.PrivateKey.key_id,
			},
			claims=json.dumps(self._build_auth_claims())
		)
		self.IdToken.make_signed_token(self.PrivateKey)

		L.info("New internal auth token issued.", struct_data={"exp": expiration})


	def _update_public_key(self):
		self.PublicKeyProvider.set_public_key(self.PrivateKey.public())


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
