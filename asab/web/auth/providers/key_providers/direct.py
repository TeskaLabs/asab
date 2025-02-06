import jwcrypto
import jwcrypto.jwk

from .abc import PublicKeyProviderABC


class DirectPublicKeyProvider(PublicKeyProviderABC):
	def __init__(self, app, auth_provider, public_key: jwcrypto.jwk.JWK | jwcrypto.jwk.JWKSet):
		super().__init__(app, auth_provider)
		if isinstance(public_key, jwcrypto.jwk.JWK):
			self.PublicKeySet.add(public_key)
		elif isinstance(public_key, jwcrypto.jwk.JWKSet):
			self.PublicKeySet = public_key
		else:
			raise ValueError("Invalid key_providers type.")

		self._set_ready(True)


	async def reload_keys(self):
		pass
