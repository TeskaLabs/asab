import aiohttp
import logging
import time

#

L = logging.getLogger(__name__)

#


def oauthclient_middleware_factory(app, *args, methods, identity_cache_longevity=60*60, **kwargs):
	"""
	Serves to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.

	:methods is a list that specifies the identification of OAuth servers such as [asab.web.authn.oauth.GitHubOAuthMethod()]
	:identity_cache_longevity is an integer that specifies the number of seconds after which the cached identity expires

	The expected format of Authorization header is:
	Authorization: Bearer <OAUTH-SERVER-ID>-<ACCESS_TOKEN>

	For more information about user info, visit:
	https://connect2id.com/products/server/docs/api/userinfo
	"""

	cache = {}

	methods_dict = {}
	for method in methods:
		methods_dict[method.get_oauth_server_id()] = method

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

		cached_identity_dict = cache.get(oauth_server_id_access_token)
		if cached_identity_dict is not None:
			expiration = cached_identity_dict.get("Expiration", time.time())
			if expiration < time.time():
				del cache[oauth_server_id_access_token]
			else:
				request.OAuthUserInfo = cached_identity_dict.get("OAuthUserInfo")
				request.Identity = cached_identity_dict.get("Identity")
				return await handler(request)

		oauth_server_id, access_token = oauth_server_id_access_token.split('-', 1)

		method = methods_dict.get(oauth_server_id)

		if method is None:
			L.warn("Method for OAuth server id '{}' was not found.".format(oauth_server_id))
			return await handler(request)

		oauth_userinfo_url = method.get_oauth_userinfo_url()
		async with aiohttp.ClientSession() as session:
			async with session.get(oauth_userinfo_url, headers={"Authorization": "{} {}".format(bearer, access_token)}) as resp:
				if resp.status == 200:
					oauth_user_info = await resp.json()
					if oauth_user_info is not None:
						request.OAuthUserInfo = oauth_user_info
						request.Identity = method.get_identity_from_oauth_user_info(oauth_user_info)
						cache[oauth_server_id_access_token] = {
							"OAuthUserInfo": request.OAuthUserInfo,
							"Identity": request.Identity,
							"Expiration": time.time() + identity_cache_longevity
						}
				else:
					raise RuntimeError("Call to OAuth server '{}' failed with status code '{}'.".format(oauth_userinfo_url, resp.status))

		return await handler(request)

	return oauthclient_middleware
