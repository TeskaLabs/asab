import abc
import typing

import jwcrypto
import jwcrypto.jwk


class PublicKeyProviderABC(abc.ABC):
	def __init__(self, app, auth_provider):
		self.App = app
		self.AuthProvider = auth_provider
		self.TaskService = self.App.get_service("asab.TaskService")
		self.PublicKeySet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()
		self._IsReady = False

	async def reload_keys(self):
		raise NotImplementedError()

	def is_ready(self) -> bool:
		return self._IsReady

	def _set_ready(self, ready: bool = True):
		self._IsReady = ready
		self.AuthProvider.check_ready()


class PublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, app, auth_provider, public_key: jwcrypto.jwk.JWK):
		super().__init__(app, auth_provider)
		self.PublicKeySet.add(public_key)
		self._set_ready(True)


	async def reload_keys(self):
		pass


class FilePublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, app, auth_provider, file_path: str, from_private_key: bool = False):
		super().__init__(app, auth_provider)
		self._load_key_file(file_path, from_private_key)

	async def reload_keys(self):
		pass

	def _load_key_file(self, file_path, from_private_key):
		if file_path.endswith(".json"):
			with open(file_path, "r") as f:
				key = jwcrypto.jwk.JWK.from_json(f.read())
		else:
			with open(file_path, "r") as f:
				key = jwcrypto.jwk.JWK.from_pem(f.read())

		if from_private_key:
			key = key.public()

		self.PublicKeySet.add(key)
		self._set_ready(True)


class UrlPublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, app, auth_provider, jwks_url: str):
		super().__init__(app, auth_provider)
		self.DiscoveryService = self.App.get_service("asab.DiscoveryService")
		self.JwksUrl = jwks_url

	async def reload_keys(self):
		if self.DiscoveryService is None:
			open_session = aiohttp.ClientSession
		else:
			open_session = self.DiscoveryService.session

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