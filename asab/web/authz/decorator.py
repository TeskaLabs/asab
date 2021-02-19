import functools

import aiohttp.web


def required(*resources):
	'''
	Checks that user authorized with access token in
	Authorization header has access to a given tenant space
	using SeaCat Auth RBAC authorization.

	It uses a cache to limit the number of HTTP checks.

	Example of use:

	@asab.web.tenant.tenant_handler
	@asab.web.authz.required("tenant:access")
	async def endpoint(self, request, *, tenant):
		...
	'''

	def decorator_required(func):

		@functools.wraps(func)
		async def wrapper(*args, **kargs):
			request = args[-1]

			# Obtain authz service from the request
			authz_service = request.AuthzService

			# Check if tenant exists in the request
			if not hasattr(request, "Tenant"):
				raise aiohttp.web.HTTPUnauthorized()

			if not await authz_service.authorize(
				resources=resources,
				tenant_id=request.Tenant.Id if hasattr(request.Tenant, "Id") else request.Tenant["_id"],
				authorization_header=request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
			):
				raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_required
