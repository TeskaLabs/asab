import aiohttp
import logging

from ...rest import json_response

#

L = logging.getLogger(__name__)

#


class OAuthForwarder(object):
	"""
	OAuthForwarder serves to add forward endpoints to the provided web server container,
	so the client applications may get/post information about the OAuth login.
	The forwarded endpoints include: POST token, GET identity, POST invalidate and POST forgot.

	OAuthForwarder expects specific instance of ABCOAuthMethod for every OAuth 2.0 server it forwards the requests to.
	Every OAuth 2.0 server is required to implement token and identity endpoints, while invalidate and forgot are optional.
	"""

	def __init__(self, *args, container, methods, **kwargs):

		# Load methods
		self.MethodsDict = {}
		for method in methods:
			self.MethodsDict[method.Config["oauth_server_id"]] = method

		# Register endpoints in the provided container
		container.WebApp.router.add_post('/token', self.token)
		container.WebApp.router.add_get('/identity', self.identity)
		container.WebApp.router.add_post('/invalidate', self.invalidate)
		container.WebApp.router.add_post('/refresh', self.refresh)

	async def token(self, request):
		"""
		Forwards "Access Token Request", see https://tools.ietf.org/html/rfc6749#section-4.1.3
		:param request: received aiohttp request
		:return: json_response
		"""
		method = await self._get_method(request)
		if method is None:
			raise aiohttp.web.HTTPNotFound()
		if len(method.Config["token_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()

		response = await self._forward_post(request, method.Config["token_url"], method.Config["client_id"], method.Config["client_secret"])
		return json_response(request=request, data=response)

	async def identity(self, request):
		"""
		Forwards "UserInfo Request", see https://connect2id.com/products/server/docs/api/userinfo
		:param request: received aiohttp request
		:return: json_response
		"""
		method = await self._get_method(request)
		if method is None:
			raise aiohttp.web.HTTPNotFound()
		if len(method.Config["identity_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()

		response = await self._forward_get(request, method.Config["identity_url"], method.Config["client_id"], method.Config["client_secret"])
		return json_response(request=request, data=response)

	async def invalidate(self, request):
		"""
		Forwards "Revocation Request", see https://tools.ietf.org/html/rfc7009#page-4
		:param request: received aiohttp request
		:return: json_response
		"""
		method = await self._get_method(request)
		if method is None:
			raise aiohttp.web.HTTPNotFound()
		if len(method.Config["invalidate_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()

		response = await self._forward_post(request, method.Config["invalidate_url"], method.Config["client_id"], method.Config["client_secret"])
		return json_response(request=request, data=response)

	async def refresh(self, request):
		"""
		Refreshes access token, see https://auth0.com/docs/tokens/refresh-token/current#use-a-refresh-token
		:param request: received aiohttp request
		:return: json_response
		"""
		method = await self._get_method(request)
		if method is None:
			raise aiohttp.web.HTTPNotFound()
		if len(method.Config["refresh_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()

		response = await self._forward_post(request, method.Config["refresh_url"], method.Config["client_id"], method.Config["client_secret"])
		return json_response(request=request, data=response)

	async def _get_method(self, request):
		oauth_server_id = request.headers.get("X-OAuthServerId")

		if oauth_server_id is None:
			L.warn("The 'X-OAuthServerId' header was not provided.")
			return None

		method = self.MethodsDict.get(oauth_server_id)
		if method is None:
			L.warn("Method for OAuth server id '{}' was not found.".format(oauth_server_id))
			return None

		return method

	async def _forward_get(self, request, url, client_id, client_secret):
		headers = await self._remove_extra_headers(dict(request.headers))
		data = dict(request.query)
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=data) as resp:
				response = {"status": resp.status}
				try:
					response["content"] = await resp.json()
					response["Content-Type"] = "application/json"
				except aiohttp.client_exceptions.ContentTypeError:
					L.warn("The response from '{}' with status code '{}' is not JSON. Using text instead.".format(url, resp.status))
					response["content"] = await resp.text()
					response["Content-Type"] = "text/html"
				return response

	async def _forward_post(self, request, url, client_id, client_secret):
		headers = await self._remove_extra_headers(dict(request.headers))
		data = dict(await request.post())
		if len(client_id) != 0:
			data["client_id"] = client_id
		if len(client_secret) != 0:
			data["client_secret"] = client_secret
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, data=data) as resp:
				response = {"status": resp.status}
				try:
					response["content"] = await resp.json()
					response["Content-Type"] = "application/json"
				except aiohttp.client_exceptions.ContentTypeError:
					L.warn("The response from '{}' with status code '{}' is not JSON. Using text instead.".format(url, resp.status))
					response["content"] = await resp.text()
					response["Content-Type"] = "text/html"
				return response

	async def _remove_extra_headers(self, headers):
		if "X-OAuthServerId" in headers:
			del headers["X-OAuthServerId"]
		# "Host" is not used in redirection. When present, it confuses f. e. GitHub OAuth server.
		if "Host" in headers:
			del headers["Host"]
		return headers
