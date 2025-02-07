import jwcrypto
import jwcrypto.jwk

from .abc import PublicKeyProviderABC


class FilePublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, auth_provider, file_path: str, from_private_key: bool = False):
		super().__init__(auth_provider)
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
