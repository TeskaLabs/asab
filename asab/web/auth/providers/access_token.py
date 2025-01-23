import typing
import jwcrypto
import jwcrypto.jwk

from .id_token import IdTokenAuthProvider
from .key_provider import LocalPublicKeyProvider
from ..utils import get_bearer_token_from_authorization_header, get_id_token_claims


class AccessTokenAuthProvider(IdTokenAuthProvider):
	"""
	Authorizes requests based on the Access Token provided in the Authorization header.

	Development only, not optimized for production use.
	"""

	def __init__(
		self,
		app,
		auth_service,
		public_key_providers: typing.Iterable[PublicKeyProviderABC],
		introspection_url: str
	):
		super().__init__(self, app, auth_service, public_key_providers)
		self.IntrospectionUrl: str = introspection_url


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		async with aiohttp.ClientSession() as session:
			async with session.post(self.IntrospectionUrl, headers=request.headers) as response:
				if response.status != 200:
					L.warning("Access token introspection failed.")
					raise aiohttp.web.HTTPUnauthorized()
				bearer_token = get_bearer_token_from_authorization_header(response)

		authz = await self._build_authorization(bearer_token)
		return authz


	async def _build_authorization(self, access_token: str, id_token: str) -> Authorization:
		"""
		Build authorization from ID token, store it in cache with access token as key.

		Args:
			access_token: Access token from Authorization header
			id_token: Base64-encoded JWToken from introspection response

		Returns:
			Valid asab.web.auth.Authorization object
		"""
		# Try if the object already exists
		authz = self.Authorizations.get(access_token)
		if authz is not None:
			try:
				authz.require_valid()
			except NotAuthenticatedError as e:
				del self.Authorizations[access_token]
				raise e
			return authz

		# Create a new Authorization object and store it
		claims = await self._get_claims_from_id_token(id_token)
		authz = Authorization(claims)

		self.Authorizations[access_token] = authz
		return authz

