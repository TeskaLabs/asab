import abc

import aiohttp.web
from ..authorization import Authorization


class AuthProviderABC(abc.ABC):
	"""
	Abstract base class for all authorization providers.
	"""
	Type = None

	def __init__(self, auth_service):
		self.AuthService = auth_service
		self.App = self.AuthService.App


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
