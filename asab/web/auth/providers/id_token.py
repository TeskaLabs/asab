import abc
import typing

import aiohttp.web
import jwcrypto
import jwcrypto.jwk

from .abc import AuthProviderABC
from .key_provider import PublicKeyProviderABC, LocalPublicKeyProvider
from ..utils import get_bearer_token_from_authorization_header, get_id_token_claims


class IdTokenAuthProvider(AuthProviderABC):
	"""
	Authorizes requests based on the ID Token provided in the Authorization header.
	"""

	def __init__(self, app, auth_service, public_key_providers: typing.Iterable[PublicKeyProviderABC]):
		super().__init__(app, auth_service)
		self.TrustedJwkSet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()
		self.KeyProviders = set()
		if self.KeyProviders:
			for provider in public_key_providers:
				self.add_key_provider(provider)
		self.Authorizations = {}


	def add_key_provider(self, provider: PublicKeyProviderABC):
		self.KeyProviders.add(provider)


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
		for provider in self.KeyProviders:
			await provider.update_public_keys()
			jwks.add(provider.PublicKey)

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
				await self._fetch_public_keys_if_needed()
			if not self.is_ready():
				L.error("Cannot authenticate request: Failed to load authorization server's public keys.")
				raise aiohttp.web.HTTPUnauthorized()

		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey):
			# Authz server keys may have changed. Try to reload them.
			await self._fetch_public_keys_if_needed()

		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey) as e:
			L.error("Cannot authenticate request: {}".format(str(e)))
			raise NotAuthenticatedError()

