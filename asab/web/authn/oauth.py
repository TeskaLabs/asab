import aiohttp


def oauthclient_middleware_factory(app, *args, oauth_userinfo_url, **kwargs):
	"""
	Serves to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.

	For more information about user info, visit:
	https://connect2id.com/products/server/docs/api/userinfo
	"""

	@aiohttp.web.middleware
	async def oauthclient_middleware(request, handler):

		authorization = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization is None:
			return await handler(request)

		async with aiohttp.ClientSession() as session:
			async with session.get(oauth_userinfo_url, headers={"Authorization": authorization}) as resp:
				if resp.status == 200:
					identity = await resp.json()
					if identity is not None:
						request.Identity = identity
				else:
					raise RuntimeError("Call to OAuth server '{}' failed with status code '{}'.".format(oauth_userinfo_url, resp.status))

		return await handler(request)

	return oauthclient_middleware
