import aiohttp
import logging

from ...rest import json_response
from ....config import ConfigObject

#

L = logging.getLogger(__name__)

#


class OAuthProxy(ConfigObject):

	ConfigDefaults = {
		"oauth_server_id": "teskalabs.com",
		"token_url": "http://localhost:8080/token_endpoint/token_request",  # POST -> to receive access token and refresh token
		"identity_url": "http://localhost:8080/identity_provider/identity",  # GET -> UserInfo identity
		"invalidate_url": "",  # POST -> Invalidate a token
		"forgot_url": "",  # POST -> Send request for a forgot password or other identity credentials
	}

	def __init__(self, config_section_name="OAuthProxy", config=None):
		super().__init__(config_section_name=config_section_name, config=config)

	def get_oauth_server_id(self):
		return self.Config["oauth_server_id"]

	async def token(self, request):
		if len(self.Config["token_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()
		response = await self._proxy_post(request, self.Config["token_url"])
		return json_response(request=request, data=response)

	async def identity(self, request):
		if len(self.Config["identity_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()
		response = await self._proxy_get(request, self.Config["identity_url"])
		return json_response(request=request, data=response)

	async def invalidate(self, request):
		if len(self.Config["invalidate_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()
		response = await self._proxy_post(request, self.Config["invalidate_url"])
		return json_response(request=request, data=response)

	async def forgot(self, request):
		if len(self.Config["forgot_url"]) == 0:
			raise aiohttp.web.HTTPNotFound()
		response = await self._proxy_post(request, self.Config["forgot_url"])
		return json_response(request=request, data=response)

	async def _proxy_get(self, request, url):
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=request.headers, params=request.query) as resp:
				if resp.status == 200:
					return await resp.json()
				else:
					return await resp.text()

	async def _proxy_post(self, request, url):
		data = await request.post()
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=request.headers, data=data) as resp:
				if resp.status == 200:
					return await resp.json()
				else:
					return await resp.text()


def add_oauth_client(*args, container, proxies, **kwargs):
	"""
	Serves to add proxy endpoints to the provided web server container,
	so the client applications may get/post information about the OAuth login.

	The proxied endpoints include: POST token, GET identity, POST invalidate and POST forgot.
	Every OAuth 2.0 server is required to implement token and identity endpoints, while invalidate and forgot are optional.
	"""

	proxies_dict = {}
	for proxy in proxies:
		proxies_dict[proxy.get_oauth_server_id()] = proxy

	async def token(request):
		proxy = await _get_proxy(request)
		if proxy is None:
			raise aiohttp.web.HTTPNotFound()
		return await proxy.token(request)

	async def identity(request):
		proxy = await _get_proxy(request)
		if proxy is None:
			raise aiohttp.web.HTTPNotFound()
		return await proxy.identity(request)

	async def invalidate(request):
		proxy = await _get_proxy(request)
		if proxy is None:
			raise aiohttp.web.HTTPNotFound()
		return await proxy.invalidate(request)

	async def forgot(request):
		proxy = await _get_proxy(request)
		if proxy is None:
			raise aiohttp.web.HTTPNotFound()
		return await proxy.forgot(request)

	async def _get_proxy(request):
		oauth_server_id = request.headers.get("X-OAuthServerId")

		if oauth_server_id is None:
			L.warn("The 'X-OAuthServerId' header was not provided.")
			return None

		proxy = proxies_dict.get(oauth_server_id)
		if proxy is None:
			L.warn("Proxy for OAuth server id '{}' was not found.".format(oauth_server_id))
			return None

		return proxy

	container.WebApp.router.add_post('/token', token)
	container.WebApp.router.add_get('/identity', identity)
	container.WebApp.router.add_post('/invalidate', invalidate)
	container.WebApp.router.add_post('/forgot', forgot)

	return container
