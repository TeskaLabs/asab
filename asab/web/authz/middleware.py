import aiohttp.web


def authz_middleware_factory(app, svc):
	"""
	Ensures that AuthzService is part of the request.
	:param app: application object
	:param svc: AuthzService
	:return: handler(request)
	"""

	@aiohttp.web.middleware
	async def authz_middleware(request, handler):
		request.AuthzService = svc
		return await handler(request)

	return authz_middleware
