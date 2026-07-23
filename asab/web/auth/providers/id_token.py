import typing
import logging
import aiohttp.web
import jwcrypto.jwt
import jwcrypto.jwk
import asab

from .abc import AuthProviderABC
from .key_providers import PublicKeyProviderABC
from ..utils import (
	get_bearer_token_from_authorization_header,
	get_bearer_token_from_websocket_request,
	get_id_token_claims,
	is_websocket_request,
)
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
		self.ResourceMatadataUrl = asab.Config.get("auth", "resource_metadata_url", fallback=None)
		self._KeyProviders = set()
		for provider in public_key_providers:
			self.register_key_provider(provider)

		self.Authorizations: typing.Dict[typing.Tuple[str, str], Authorization] = {}

		self.App.PubSub.subscribe("PublicKey.updated!", self.collect_keys)
		self.App.PubSub.subscribe("Application.housekeeping!", self._delete_invalid_authorizations)
		self.App.TaskService.schedule(self._update_public_keys())


	def register_key_provider(self, provider: PublicKeyProviderABC):
		self._KeyProviders.add(provider)
		self.collect_keys()


	async def initialize(self):
		pass


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		if not self._KeyProviders:
			L.debug("No public key providers are registered; ID token authentication cannot verify signatures.")
			raise NotAuthenticatedError(
				resource_metadata=self.ResourceMatadataUrl,
				message="No public key providers registered",
			)


		if is_websocket_request(request):
			try:
				# Post-introspection WS request has an Authorization header
				token = get_bearer_token_from_authorization_header(request)
			except NotAuthenticatedError as e:
				# Internal network WS request
				token = get_bearer_token_from_websocket_request(request)
		else:
			token = get_bearer_token_from_authorization_header(request)

		try:
			authz = await self._build_authorization(token)
			return authz
		except NotAuthenticatedError as e:
			e.update_www_authenticate(resource_metadata=self.ResourceMatadataUrl)
			raise e


	def collect_keys(self, *args, **kwargs):
		"""
		Collect public keys from all key providers into a single trusted JWK set.
		"""
		jwks = jwcrypto.jwk.JWKSet()
		for provider in self._KeyProviders:
			for key in provider.public_keys():
				jwks.add(key)
		self.TrustedJwkSet = jwks


	async def _update_public_keys(self):
		"""
		Update the public keys from all key providers.
		"""
		for provider in list(self._KeyProviders):
			await provider.reload_keys()
		self.collect_keys()


	async def _build_authorization(self, token: typing.Tuple[str, str]) -> Authorization:
		"""
		Build authorization from ID token.

		Args:
			token: Tuple of authentication scheme (must be Bearer) and token value (Base64-encoded ID token)

		Returns:
			Valid asab.web.auth.Authorization object
		"""
		auth_scheme, token_value = token
		if auth_scheme != "bearer":
			L.debug(
				"Unsupported Authorization header scheme for ID token authentication.",
				struct_data={"scheme": auth_scheme},
			)
			raise NotAuthenticatedError(message="Unsupported Authorization scheme (expected Bearer)")

		# Try if the object already exists
		authz = self.Authorizations.get(token)
		if authz is not None:
			try:
				authz.require_valid()
			except NotAuthenticatedError as e:
				del self.Authorizations[token]
				raise e
			return authz

		# Create a new Authorization object and store it
		claims = await self._get_claims_from_id_token(token_value)
		authz = Authorization(claims, id_token=token_value)

		self.Authorizations[token] = authz
		return authz


	async def _get_claims_from_id_token(self, id_token):
		"""
		Parse the bearer ID token and extract auth claims.
		"""
		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey):
			# Authz server keys may have changed or are not ready yet. Try to reload them.
			await self._update_public_keys()

		try:
			return get_id_token_claims(id_token, self.TrustedJwkSet)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey) as e:
			L.debug("Cannot authenticate request: {}".format(str(e)))
			raise NotAuthenticatedError(message="ID token signature verification failed")


	def _delete_invalid_authorizations(self, *args, **kwargs):
		"""
		Delete invalid authorizations.
		"""
		expired = set()
		for id_token, authz in self.Authorizations.items():
			if not authz.is_valid():
				expired.add(id_token)

		for id_token in expired:
			del self.Authorizations[id_token]
