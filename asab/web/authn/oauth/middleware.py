import aiohttp


def oauthclient_middleware_factory(app, *args, methods, **kwargs):
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
			return await handler(request)

		bearer = bearer_oauth[0]
		oauth_server_id_access_token = bearer_oauth[1].split('-')

		if len(oauth_server_id_access_token) < 2:
			return await handler(request)

		oauth_server_id = oauth_server_id_access_token[0]
		access_token = oauth_server_id_access_token[1]

		selected_method = None
		for method in methods:
			if method.get_oauth_server_id() == oauth_server_id:
				selected_method = method
				break

		if selected_method is None:
			return await handler(request)

		oauth_userinfo_url = selected_method.get_oauth_userinfo_url()
		async with aiohttp.ClientSession() as session:
			async with session.get(oauth_userinfo_url, headers={"Authorization": "{} {}".format(bearer, access_token)}) as resp:
				if resp.status == 200:
					oauth_user_info = await resp.json()
					if oauth_user_info is not None:
						request.OAuthUserInfo = oauth_user_info
						request.Identity = selected_method.get_identity_from_oauth_user_info(oauth_user_info)
				else:
					raise RuntimeError("Call to OAuth server '{}' failed with status code '{}'.".format(oauth_userinfo_url, resp.status))

		return await handler(request)

	return oauthclient_middleware
