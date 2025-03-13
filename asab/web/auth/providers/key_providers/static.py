import typing
import jwcrypto
import jwcrypto.jwk

from .abc import PublicKeyProviderABC


class StaticPublicKeyProvider(PublicKeyProviderABC):
	"""
	Static auth server key provider.
	The key has to be provided through a variable or a file.
	"""
	Type = "static"

	def __init__(
		self, app, *,
		public_key: typing.Optional[typing.Union[jwcrypto.jwk.JWK, jwcrypto.jwk.JWKSet]] = None
	):
		super().__init__(app)
		if public_key is not None:
			self.set_public_key(public_key)


	def set_public_key(self, public_key: typing.Union[jwcrypto.jwk.JWK, jwcrypto.jwk.JWKSet]):
		"""
		Directly set key (or key set) to be used for auth validation.

		Args:
			public_key: JWKey or JWKey set.
		"""
		self._set_keys(public_key)


	def set_public_key_from_file(self, file_path, from_private_key: bool = False):
		"""
		Load key from a file.

		Args:
			file_path: Path to the file with the key.
			from_private_key: If True, the key is loaded as a private key and the public key is derived.
		"""
		if file_path.endswith(".json"):
			with open(file_path, "r") as f:
				key = jwcrypto.jwk.JWK.from_json(f.read())
		else:
			with open(file_path, "r") as f:
				key = jwcrypto.jwk.JWK.from_pem(f.read())

		if from_private_key:
			key = key.public()

		self._set_keys(key)


	async def reload_keys(self):
		pass
