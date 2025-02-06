import abc
import logging
import jwcrypto
import jwcrypto.jwk
import aiohttp
import json


L = logging.getLogger(__name__)


class PublicKeyProviderABC(abc.ABC):
	def __init__(self, auth_provider):
		self.AuthProvider = auth_provider
		self.App = self.AuthProvider.App
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
