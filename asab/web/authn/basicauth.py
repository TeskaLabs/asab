import aiohttp.web


def basicauth_middleware_factory(app, *args, **kwargs):

	@aiohttp.web.middleware
	async def basicauth_middleware(request, handler):
		auth_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
		if auth_header is None:
			return await handler(request)

		auth = aiohttp.BasicAuth.decode(auth_header=auth_header, encoding='utf-8')
		request.Identity = auth.login

		# TODO: Check the password if required

		return await handler(request)

	return basicauth_middleware
