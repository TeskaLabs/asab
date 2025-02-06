import abc

import aiohttp.web
from ..authorization import Authorization


class AuthProviderABC(abc.ABC):
	"""
	Abstract base class for all authorization providers.
	"""

	def __init__(self, auth_service):
		self.AuthService = auth_service
		self.App = self.AuthService.App
		self._IsReady = False


	async def initialize(self):
		raise NotImplementedError()


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		"""
		Authorize the web request.

		Args:
			request (aiohttp.web.Request): The web request to authorize.

		Returns:
			Authorization: Authorization object.
		"""
		raise NotImplementedError()


	def is_ready(self) -> bool:
		return self._IsReady


	def _set_ready(self, ready: bool = True):
		self._IsReady = ready
		self.AuthService.check_ready()
