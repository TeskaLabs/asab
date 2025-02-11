import abc

import aiohttp.web
from ..authorization import Authorization


class AuthProviderABC(abc.ABC):
	"""
	Authenticates and authorizes web requests.
	"""
	Type = None

	def __init__(self, app):
		self.App = app


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
