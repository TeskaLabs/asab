import aiohttp
import logging

#

L = logging.getLogger(__name__)

#


def oauthclient_middleware_factory(app, *args, oauth_client_service, **kwargs):
	"""
	Serves to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.

	The expected format of Authorization header is:
	Authorization: Bearer <OAUTH-SERVER-ID>-<ACCESS_TOKEN>

	For more information about user info, visit:
	https://connect2id.com/products/server/docs/api/userinfo
	"""

	@aiohttp.web.middleware
	async def oauthclient_middleware(request, handler):

		authorization = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization is None:
			return await handler(request)

		bearer_oauth = authorization.split(' ')
		if len(bearer_oauth) < 2:
			L.warn("Authorization header '{}' is not in proper 'Bearer <OAUTH-SERVER-ID>-<ACCESS_TOKEN>' format.".format(authorization))
			return await handler(request)

		bearer = bearer_oauth[0]
		oauth_server_id_access_token = bearer_oauth[1]

		if "-" not in oauth_server_id_access_token:
			L.warn("Authorization header's bearer '{}' is not in proper '<OAUTH-SERVER-ID>-<ACCESS_TOKEN>' format.".format(bearer_oauth[1]))
			return await handler(request)

		identity = oauth_client_service.IdentityCache[oauth_server_id_access_token]
		if identity is not None:
			# This is "cache hit" branch
			request.OAuthUserInfo = identity.get("OAuthUserInfo")
			request.Identity = identity.get("Identity")
			return await handler(request)

		oauth_server_id, access_token = oauth_server_id_access_token.split('-', 1)

		method = oauth_client_service.Methods.get(oauth_server_id)

		if method is None:
			L.warn("Method for OAuth server id '{}' was not found.".format(oauth_server_id))
			return await handler(request)

		oauth_userinfo_url = method.Config["identity_url"]
		async with aiohttp.ClientSession() as session:
			async with session.get(oauth_userinfo_url, headers={"Authorization": "{} {}".format(bearer, access_token)}) as resp:
				if resp.status == 200:
					oauth_user_info = await resp.json()
					if oauth_user_info is not None:
						request.OAuthUserInfo = oauth_user_info
						request.Identity = method.extract_identity(oauth_user_info)
						oauth_client_service.IdentityCache[oauth_server_id_access_token] = (request.OAuthUserInfo, request.Identity)
				else:
					# "authn_required_handler" decorator will then return "HTTPUnauthorized" to the client,
					# because of missing identity in the request
					assert not hasattr(request, "Identity")
					L.warn("Call to OAuth server '{}' failed with status code '{}'.".format(oauth_userinfo_url, resp.status))

		return await handler(request)

	return oauthclient_middleware
