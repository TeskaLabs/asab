import aiohttp
import logging
import re

#

L = logging.getLogger(__name__)

#


def oauthclient_middleware_factory(app, *args, oauth_client_service, **kwargs):
	"""
	Serves to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.

	The expected format of Authorization header is:
	Authorization: Bearer <ACCESS_TOKEN>
	X-Authorization-OAuth-Server: <OAUTH-SERVER-ID>

	For more information about user info, visit:
	https://connect2id.com/products/server/docs/api/userinfo
	"""

	# Bearer token Regex is based on RFC 6750
	# The OAuth 2.0 Authorization Framework: Bearer Token Usage
	# Chapter 2.1. Authorization Request Header Field
	AuthorizationHeaderRg = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)")

	@aiohttp.web.middleware
	async def oauthclient_middleware(request, handler):

		# Check that the identity is not already inserted
		assert not hasattr(request, "Identity")

		authorization = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization is None:
			return await handler(request)

		am = AuthorizationHeaderRg.match(authorization)
		if am is None:
			L.warn("Authorization header '{}' is not in format.".format(authorization))
			return await handler(request)
		access_token = am.group(1)

		method, oauth_user_info, expired_at = oauth_client_service.UserInfoCache.get(access_token, (None, None, None))
		if expired_at is not None and expired_at < app.Loop.time():
			# Cache entry is expired
			del oauth_client_service.UserInfoCache[access_token]
			method, oauth_user_info, expired_at = None, None, None

		if oauth_user_info is None:
			oauth_server_id = request.headers.get('X-Authorization-OAuth-Server', None)
			method = oauth_client_service.get_method(oauth_server_id)
			if method is None:
				L.warn("Method for OAuth server id '{}' was not found.".format(oauth_server_id))
				return await handler(request)

			userinfo_url = method.Config["userinfo_url"]
			headers = {
				"Authorization": authorization,
			}
			async with aiohttp.ClientSession() as session:
				async with session.get(userinfo_url, headers=headers) as resp:
					if resp.status == 200:
						oauth_user_info = await resp.json()

						expired_at = app.Loop.time() + oauth_client_service.UserInfoCacheLongevity
						oauth_client_service.UserInfoCache[access_token] = (method, oauth_user_info, expired_at)
					else:
						# "authn_required_handler" decorator will then return "HTTPUnauthorized" to the client,
						# because of missing identity in the request
						L.warn("Call to OAuth server '{}' failed with status code '{}'.".format(userinfo_url, resp.status))

		if oauth_user_info is not None:
			request.UserInfo = oauth_user_info
			request.Identity = method.extract_identity(oauth_user_info)
		else:
			oauth_client_service.UserInfoCache.pop(access_token, None)

		return await handler(request)

	return oauthclient_middleware
