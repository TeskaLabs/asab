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
	Type = None

	def __init__(self, app):
		self.App = app
		self.TaskService = self.App.get_service("asab.TaskService")
		self.PublicKeySet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()


	async def reload_keys(self):
		raise NotImplementedError()


	def public_keys(self):
		for key in self.PublicKeySet["keys"]:
			yield key


	def _set_keys(self, keys: typing.Optional[typing.Union[jwcrypto.jwk.JWK, jwcrypto.jwk.JWKSet]]):
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

		self.App.PubSub.publish("PublicKey.updated!", self, asynchronously=False)
