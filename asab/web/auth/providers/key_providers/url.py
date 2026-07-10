import logging
import jwcrypto
import jwcrypto.jwk
import aiohttp
import json

from .abc import PublicKeyProviderABC


L = logging.getLogger(__name__)


class UrlPublicKeyProvider(PublicKeyProviderABC):
	"""
	Public key provider that loads auth server keys from a URL.
	"""
	Type = "url"

	def __init__(self, app, jwks_url: str):
		super().__init__(app)
		self.JwksUrl = jwks_url


	async def reload_keys(self):
		discovery_service = self.App.get_service("asab.DiscoveryService")
		if discovery_service is not None:
			open_session = discovery_service.session
		else:
			open_session = aiohttp.ClientSession

		async with open_session() as session:
			jwks = await _fetch_jwks(session, self.JwksUrl)

		if jwks is not None:
			self._set_keys(jwks)
			L.debug("Auth server public keys loaded.", struct_data={"url": self.JwksUrl})


async def _fetch_jwks(session: aiohttp.ClientSession, url: str):
	try:
		async with session.get(url) as response:
			if response.status != 200:
				L.error(
					"Auth server JWKS endpoint returned a non-200 HTTP status.",
					struct_data={
						"status": response.status,
						"url": url,
						"text": await response.text(),
					},
				)
				return

			try:
				data = await response.json()
			except json.JSONDecodeError:
				L.error(
					"Auth server JWKS endpoint returned a response that is not valid JSON.",
					struct_data={"url": url},
				)
				return

	except aiohttp.client_exceptions.ClientConnectorError:
		L.error(
			"Cannot reach auth server JWKS endpoint to load public keys.",
			struct_data={"url": url},
		)
		return

	try:
		keys = data["keys"]
	except (IndexError, KeyError):
		L.error(
			"Auth server JWKS response does not contain any public keys.",
			struct_data={"url": url},
		)
		return

	jwks = jwcrypto.jwk.JWKSet()
	for key in keys:
		try:
			jwks.add(jwcrypto.jwk.JWK(**key))
		except Exception:
			L.error(
				"Auth server JWKS response contains a key that could not be decoded.",
				struct_data={"url": url},
			)
			return

	return jwks
