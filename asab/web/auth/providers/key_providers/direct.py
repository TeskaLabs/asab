import typing

import jwcrypto
import jwcrypto.jwk

from .abc import PublicKeyProviderABC


class DirectPublicKeyProvider(PublicKeyProviderABC):
	def __init__(
		self,
		auth_provider,
		public_key: typing.Optional[jwcrypto.jwk.JWK | jwcrypto.jwk.JWKSet] = None
	):
		super().__init__(auth_provider)
		if public_key is not None:
			self.set_public_key(public_key)


	def set_public_key(self, public_key: jwcrypto.jwk.JWK | jwcrypto.jwk.JWKSet):
		if isinstance(public_key, jwcrypto.jwk.JWK):
			self.PublicKeySet.add(public_key)
		elif isinstance(public_key, jwcrypto.jwk.JWKSet):
			self.PublicKeySet = public_key
		else:
			raise ValueError("Invalid public_key type.")
		self._set_ready(True)


	async def reload_keys(self):
		pass
