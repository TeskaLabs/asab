import abc
import aiohttp
import logging

from ...rest import json_response

#

L = logging.getLogger(__name__)

#


class ABCOAuthProxy(abc.ABC):

	@abc.abstractmethod
	def get_oauth_server_id(self):
		pass

	@abc.abstractmethod
	def get_token_url(self):
		pass

	@abc.abstractmethod
	def get_identity_url(self):
		pass

	@abc.abstractmethod
	def get_invalidate_url(self):
		pass

	@abc.abstractmethod
	def get_forgot_url(self):
		pass


class GitHubOAuthProxy(ABCOAuthProxy):

	def get_oauth_server_id(self):
		return "github.com"

	def get_token_url(self):
		return "https://github.com/login/oauth/access_token"

	def get_identity_url(self):
		return "https://api.github.com/user"

	def get_invalidate_url(self):
		return None

	def get_forgot_url(self):
		return None


def oauthclient_proxy_factory(*args, container, proxies, **kwargs):
	"""
	Serves to add proxy endpoints to the provided web server container,
	so the client applications may get/post information about the OAuth login.

	The proxied endpoints include: POST token, GET identity, POST invalidate and POST forgot.
	Every OAuth 2.0 server is required to implement token and identity endpoints, while invalidate and forgot are optional.
	"""

	proxies_dict = {}
	for proxy in proxies:
		proxies_dict[proxy.get_oauth_server_id()] = proxy

	# POST -> to receive access token and refresh token
	async def token(request):
		proxy = await _parse_proxy(request)
		if proxy is None or proxy.get_token_url() is None:
			raise aiohttp.web.HTTPNotFound()
		response = await _proxy_post(request, proxy.get_token_url())
		return json_response(request=request, data=response)

	# GET -> UserInfo identity
	async def identity(request):
		proxy = await _parse_proxy(request)
		if proxy is None or proxy.get_identity_url() is None:
			raise aiohttp.web.HTTPNotFound()
		response = await _proxy_get(request, proxy.get_identity_url())
		return json_response(request=request, data=response)

	# POST -> Invalidate a token
	async def invalidate(request):
		proxy = await _parse_proxy(request)
		if proxy is None or proxy.get_invalidate_url() is None:
			raise aiohttp.web.HTTPNotFound()
		response = await _proxy_post(request, proxy.get_invalidate_url())
		return json_response(request=request, data=response)

	# POST -> Send request for a forgot password or other identity credentials
	async def forgot(request):
		proxy = await _parse_proxy(request)
		if proxy is None or proxy.get_forgot_url() is None:
			raise aiohttp.web.HTTPNotFound()
		response = await _proxy_post(request, proxy.get_forgot_url())
		return json_response(request=request, data=response)

	async def _parse_proxy(request):
		oauth_server_id = request.headers.get("X-OAuthServerId")

		if oauth_server_id is None:
			L.warn("The 'X-OAuthServerId' header was not provided.")
			return None

		proxy = proxies_dict.get(oauth_server_id)
		if proxy is None:
			L.warn("Proxy for OAuth server id '{}' was not found.".format(oauth_server_id))
			return None

		return proxy

	async def _proxy_get(request, url):
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=request.headers, params=request.query) as resp:
				if resp.status == 200:
					return await resp.json()
				else:
					return await resp.text()

	async def _proxy_post(request, url):
		data = await request.post()
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=request.headers, data=data) as resp:
				if resp.status == 200:
					return await resp.json()
				else:
					return await resp.text()

	container.WebApp.router.add_post('/token', token)
	container.WebApp.router.add_get('/identity', identity)
	container.WebApp.router.add_post('/invalidate', invalidate)
	container.WebApp.router.add_post('/forgot', forgot)

	return container
