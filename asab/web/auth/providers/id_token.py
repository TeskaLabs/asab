import typing
import logging
import aiohttp.web
import jwcrypto
import jwcrypto.jwk

from .abc import AuthProviderABC
from .key_providers import (
	PublicKeyProviderABC,
	FilePublicKeyProvider,
	DirectPublicKeyProvider,
	UrlPublicKeyProvider
)
from ..utils import get_bearer_token_from_authorization_header, get_id_token_claims
from ..authorization import Authorization
from ....exceptions import NotAuthenticatedError


L = logging.getLogger(__name__)


class IdTokenAuthProvider(AuthProviderABC):
	"""
	Authenticates and authorizes requests based on the ID Token provided in the Authorization header.
	"""
	Type = "id_token"

	def __init__(self, app, public_key_providers: typing.Iterable[PublicKeyProviderABC] = ()):
		super().__init__(app)
		self.TrustedJwkSet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()
		self._KeyProviders = set()
		if self._KeyProviders:
			for provider in public_key_providers:
				self.add_key_provider(provider)
		self.Authorizations = {}

		self.App.PubSub.subscribe("Application.housekeeping!", self._delete_invalid_authorizations)
		self.App.TaskService.schedule(self._update_public_keys())


	def add_key_provider(self, provider: PublicKeyProviderABC):
		self._KeyProviders.add(provider)


	def add_jwks_url(self, jwks_url: str):
		self.add_key_provider(
			UrlPublicKeyProvider(self.App, jwks_url)
		)


	def add_public_key(self, public_key: jwcrypto.jwk.JWK | jwcrypto.jwk.JWKSet):
		self.add_key_provider(
			DirectPublicKeyProvider(self.App, public_key)
		)


	def add_public_key_from_file(self, file_path: str, from_private_key: bool = False):
		self.add_key_provider(
			FilePublicKeyProvider(self.App, file_path, from_private_key)
		)


	async def initialize(self):
		pass


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		bearer_token = get_bearer_token_from_authorization_header(request)
		authz = await self._build_authorization(bearer_token)
		return authz


	async def _update_public_keys(self):
		"""
		Update the public keys from all key providers.
		"""
		jwks = jwcrypto.jwk.JWKSet()
		for provider in self._KeyProviders:
			await provider.reload_keys()
			jwks.update(provider.PublicKeySet)

		self.TrustedJwkSet = jwks


	async def _build_authorization(self, id_token: str) -> Authorization:
		"""
		Build authorization from ID token.

		Args:
			id_token: Base64-encoded JWToken from Authorization header

		Returns:
			Valid asab.web.auth.Authorization object
		"""
		# Try if the object already exists
		authz = self.Authorizations.get(id_token)
		if authz is not None:
			try:
				authz.require_valid()
			except NotAuthenticatedError as e:
				del self.Authorizations[id_token]
				raise e
			return authz

		# Create a new Authorization object and store it
		claims = await self._get_claims_from_id_token(id_token)
		authz = Authorization(claims)

		self.Authorizations[id_token] = authz
		return authz


	async def _get_claims_from_id_token(self, id_token):
		"""
		Parse the bearer ID token and extract user info.
		"""
		if not self.is_ready():
			# Try to load the public keys again
			if not self.TrustedJwkSet["keys"]:
				await self._update_public_keys()
			if not self.is_ready():
				L.error("Cannot authenticate request: Failed to load authorization server's public keys.")
				raise NotAuthenticatedError()

		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey):
			# Authz server keys may have changed. Try to reload them.
			await self._update_public_keys()

		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey) as e:
			L.error("Cannot authenticate request: {}".format(str(e)))
			raise NotAuthenticatedError()


	def _delete_invalid_authorizations(self):
		"""
		Delete invalid authorizations.
		"""
		for id_token, authz in list(self.Authorizations.items()):
			if not authz.is_valid():
				del self.Authorizations[id_token]
