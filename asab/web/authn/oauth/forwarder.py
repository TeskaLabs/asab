import aiohttp
import logging

import jwt
import base64
import json

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

	def __init__(self, *args, container, service, **kwargs):

		self.Service = service

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

		# Extract the identity from the token right now and store it in the identity cache
		oauth_server_public_key = method.Config["oauth_server_public_key"].encode("utf-8")
		if self.Service.IdentityCache is not None and len(oauth_server_public_key) > 0 and response.get("status") == 200:
			content = response.get("content")
			if not isinstance(content, dict):
				L.warning("The received response '{}' was not in expected format.".format(json.dumps(response)))
				return json_response(request=request, data=response)

			# Receive access token and token ID from the response
			access_token = content.get("access_token")
			token_id = content.get("token_id")
			if access_token is None or token_id is None:
				L.warning("Skipping identity store. The received response '{}' was not in expected format.".format(json.dumps(response)))
				return json_response(request=request, data=response)

			# Decode token from token id: https://www.oauth.com/oauth2-servers/access-tokens/self-encoded-access-tokens/
			try:
				token = jwt.decode(token_id.encode("utf-8"), oauth_server_public_key, audience='client_id="{}"'.format(method.Config["client_id"]), algorithm='RS256')
			except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidAudienceError):
				L.warning("Token ID '{}' could not be decoded. Did you specify the OAuth server '{}' public key correctly?".format(token_id, method.Config["oauth_server_id"]))
				return json_response(request=request, data=response)

			# Access token validation: https://openid.net/specs/openid-connect-core-1_0.html#3.1.3.8
			at_hash = token.get("at_hash")
			computed_at_hash = base64.urlsafe_b64encode(access_token[0:len(access_token) // 2].encode("utf-8")).decode("utf-8")
			if computed_at_hash != at_hash:
				L.warning("The access token '{}' from '{}' could not be validated.".format(access_token, method.Config["oauth_server_id"]))
				return json_response(request=request, data=response)

			# Identity format validation (OpenID Connect expects identity in "sub")
			identity = token.get("sub")
			if identity is None:
				L.warning("Identity from '{}' was not in expected format.".format(method.Config["oauth_server_id"]))
				return json_response(request=request, data=response)

			# Store the identity in cache
			oauth_server_id_access_token = "{}-{}".format(method.Config["oauth_server_id"], access_token)
			self.Service.IdentityCache[oauth_server_id_access_token] = ({"sub": identity}, identity)

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
		if len(method.Config["userinfo_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()

		response = await self._forward_get(
			request,
			method.Config["userinfo"],
			method.Config["client_id"],
			method.Config["client_secret"]
		)
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
			L.warning("The 'X-OAuthServerId' header was not provided.")
			return None

		method = self.Service.Methods.get(oauth_server_id)
		if method is None:
			L.warning("Method for OAuth server id '{}' was not found.".format(oauth_server_id))
			return None

		return method

	async def _forward_get(self, request, url, client_id, client_secret):
		# Construct headers
		headers = {}
		auth = request.headers.get("Authorization")
		if auth is not None:
			headers["Authorization"] = auth
		# Construct request
		data = dict(request.query)
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=data) as resp:
				response = {"status": resp.status}
				try:
					response["content"] = await resp.json()
					response["Content-Type"] = "application/json"
				except aiohttp.client_exceptions.ContentTypeError:
					L.warning("The response from '{}' with status code '{}' is not JSON. Using text instead.".format(url, resp.status))
					response["content"] = await resp.text()
					response["Content-Type"] = "text/html"
				return response

	async def _forward_post(self, request, url, client_id, client_secret):
		data = dict(await request.post())
		if len(client_id) != 0:
			data["client_id"] = client_id
		if len(client_secret) != 0:
			data["client_secret"] = client_secret
		async with aiohttp.ClientSession() as session:
			async with session.post(url, data=data) as resp:
				response = {"status": resp.status}
				try:
					response["content"] = await resp.json()
					response["Content-Type"] = "application/json"
				except aiohttp.client_exceptions.ContentTypeError:
					L.warning("The response from '{}' with status code '{}' is not JSON. Using text instead.".format(url, resp.status))
					response["content"] = await resp.text()
					response["Content-Type"] = "text/html"
				return response
