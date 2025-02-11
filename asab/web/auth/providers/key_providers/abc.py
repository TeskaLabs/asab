import abc
import logging
import jwcrypto
import jwcrypto.jwk


L = logging.getLogger(__name__)


class PublicKeyProviderABC(abc.ABC):
	"""
	Provides authorization server public keys.
	"""

	def __init__(self, app):
		self.App = app
		self.TaskService = self.App.get_service("asab.TaskService")
		self.PublicKeySet: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()

	async def reload_keys(self):
		raise NotImplementedError()
