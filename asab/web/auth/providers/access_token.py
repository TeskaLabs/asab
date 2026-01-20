import typing
import logging
import aiohttp.web

from .id_token import IdTokenAuthProvider
from asab.web.auth.providers.key_providers.abc import PublicKeyProviderABC
from ..utils import get_bearer_token_from_authorization_header
from ..authorization import Authorization
from ....exceptions import NotAuthenticatedError


L = logging.getLogger(__name__)


class AccessTokenAuthProvider(IdTokenAuthProvider):
	"""
	Authenticates and authorizes requests based on the Access Token provided in the Authorization header.
	Seacat Auth Nginx introspection is used to validate the token.

	Development only, not optimized for production use.
	"""
	Type = "access_token"

	def __init__(
		self,
		app,
		introspection_url: str,
		public_key_providers: typing.Iterable[PublicKeyProviderABC] = (),
	):
		super().__init__(app)
		self.IntrospectionUrl: str = introspection_url


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		try:
			return await self._authorize(request)
		except NotAuthenticatedError as e:
			e.update_www_authenticate(resource_metadata=self.ResourceMatadataUrl)
			raise e


	async def _authorize(self, request: aiohttp.web.Request) -> Authorization:
		access_token = None
		if request.headers.get('connection').lower() == 'upgrade':
			# Special handling for WebSocket connections
			protocol = request.headers.get('sec-websocket-protocol')
			if protocol is not None:
				for p in protocol.split(', '):
					if not p.startswith('access_token_'):
						continue
					access_token = p.split('access_token_')[1]
					break

		if access_token is None:
			access_token = get_bearer_token_from_authorization_header(request)

		# Try if the access token is already known
		authz = self.Authorizations.get(access_token)
		if authz is not None:
			try:
				authz.require_valid()
			except NotAuthenticatedError as e:
				del self.Authorizations[access_token]
				raise e
			return authz

		# Introspect the request
		async with aiohttp.ClientSession() as session:
			async with session.post(self.IntrospectionUrl, headers=request.headers) as response:
				if response.status != 200:
					L.warning("Access token introspection failed.")
					raise NotAuthenticatedError()
				id_token = get_bearer_token_from_authorization_header(response)

		# Create a new Authorization object and store it
		claims = await self._get_claims_from_id_token(id_token)
		authz = Authorization(claims, id_token=id_token)

		self.Authorizations[access_token] = authz
		return authz
