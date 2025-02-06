import logging
import jwcrypto
import jwcrypto.jwk
import aiohttp
import json

from .abc import PublicKeyProviderABC


L = logging.getLogger(__name__)


class UrlPublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, auth_provider, jwks_url: str):
		super().__init__(auth_provider)
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
			self.PublicKeySet = jwks
			L.debug("Public key set loaded.", struct_data={"url": self.JwksUrl})
			self._set_ready(True)
		else:
			self._set_ready(False)


async def _fetch_jwks(session: aiohttp.ClientSession, url: str):
	try:
		async with session.get(url) as response:
			if response.status != 200:
				L.error("HTTP error while loading public keys.", struct_data={
					"status": response.status,
					"url": url,
					"text": await response.text(),
				})
				return

			try:
				data = await response.json()
			except json.JSONDecodeError:
				L.error("JSON decoding error while loading public keys.", struct_data={
					"url": url,
					"data": data,
				})
				return

	except aiohttp.client_exceptions.ClientConnectorError as e:
		L.error("Connection error while loading public keys: {}".format(e), struct_data={
			"url": url,
		})
		return

	try:
		keys = data["keys"]
	except (IndexError, KeyError):
		L.error("Error while loading public keys: No public keys in server response.", struct_data={
			"url": url,
			"data": data,
		})
		return

	jwks = jwcrypto.jwk.JWKSet()
	for key in keys:
		try:
			jwks.add(jwcrypto.jwk.JWK(**key))
		except Exception as e:
			L.error("JWK decoding error while loading public keys: {}.".format(e), struct_data={
				"url": url,
				"data": data,
			})
			return

	return jwks
