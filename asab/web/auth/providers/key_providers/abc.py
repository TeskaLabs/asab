import abc
import logging
import typing
import jwcrypto
import jwcrypto.jwk


L = logging.getLogger(__name__)


class PublicKeyProviderABC(abc.ABC):
	"""
	Provides authorization server public keys.
	"""

	def __init__(self, app):
		self.App = app
		self.AuthProviders = set()  # Auth providers that use this public key provider
		self.TaskService = self.App.get_service("asab.TaskService")
		self.PublicKeySet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()


	async def reload_keys(self):
		raise NotImplementedError()


	def _set_keys(self, keys: typing.Optional[jwcrypto.jwk.JWK | jwcrypto.jwk.JWKSet]):
		"""
		Update public key set and notify all auth providers that use this key provider.

		Args:
			keys: JWKey, JWKey set or None.
		"""
		if keys is None:
			self.PublicKeySet = jwcrypto.jwk.JWKSet()
		elif isinstance(keys, jwcrypto.jwk.JWK):
			jwks = jwcrypto.jwk.JWKSet()
			jwks.add(keys)
			self.PublicKeySet = jwks
		elif isinstance(keys, jwcrypto.jwk.JWKSet):
			self.PublicKeySet = keys
		else:
			raise ValueError("Invalid public_key type.")

		for auth_provider in self.AuthProviders:
			auth_provider.collect_keys()
