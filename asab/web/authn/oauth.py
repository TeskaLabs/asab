import aiohttp

import asab
import asab.web.rest


def oauthclient_middleware_factory(app, *args, url, **kwargs):

	@aiohttp.web.middleware
	async def oauthclient_middleware(request, handler):

		authorization = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization is None:
			return asab.web.rest.json_response(request, {
				"result": "AUTHORIZATION-NOT-PROVIDED"
			})

		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers={"Authorization": authorization}) as resp:
				if resp.status == 200:
					identity = await resp.json()
					if identity is not None:
						request.Identity = identity
						return await handler(request)
				else:
					return asab.web.rest.json_response(request, {
						"result": "AUTHORIZATION-FAILED"
					})

		return asab.web.rest.json_response(request, {
			"result": "AUTHORIZATION-ERROR"
		})

	return oauthclient_middleware
