import aiohttp

import asab
import asab.web.rest


def oauthclient_middleware_factory(app, *args, url, **kwargs):

	@aiohttp.web.middleware
	async def oauthclient_middleware(request, handler):

		authorization = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization is None:
			return await handler(request)

		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers={"Authorization": authorization}) as resp:
				if resp.status == 200:
					identity = await resp.json()
					if identity is not None:
						request.Identity = identity
				else:
					raise RuntimeError("Call to OAuth server '{}' failed with status code '{}'.".format(url, resp.status))

		return await handler(request)

	return oauthclient_middleware
