import aiohttp
import logging

#

L = logging.getLogger(__name__)

#


def oauthclient_middleware_factory(app, *args, methods, **kwargs):
	"""
	Serves to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.

	The expected format of Authorization header is:
	Authorization: Bearer <OAUTH-SERVER-ID>-<ACCESS_TOKEN>

	For more information about user info, visit:
	https://connect2id.com/products/server/docs/api/userinfo
	"""

	methods_dict = {}
	for method in methods:
		methods_dict[method.Config["oauth_server_id"]] = method

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

		if "-" not in bearer_oauth[1]:
			L.warn("Authorization header's bearer '{}' is not in proper '<OAUTH-SERVER-ID>-<ACCESS_TOKEN>' format.".format(bearer_oauth[1]))
			return await handler(request)

		oauth_server_id, access_token = bearer_oauth[1].split('-', 1)

		method = methods_dict.get(oauth_server_id)

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
				else:
					raise RuntimeError("Call to OAuth server '{}' failed with status code '{}'.".format(oauth_userinfo_url, resp.status))

		return await handler(request)

	return oauthclient_middleware
