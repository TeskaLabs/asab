import functools
import re

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

	authorization_header_rg = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)")

	def decorator_required(func):

		@functools.wraps(func)
		async def wrapper(*args, **kargs):
			request = args[-1]

			# Obtain authz service from the request
			authz_service = request.AuthzService

			access_token = None
			authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)

			# Obtain access token from the authorization header
			if authorization_header is not None:
				authorization_match = authorization_header_rg.match(authorization_header)
				if authorization_match is not None:
					access_token = authorization_match.group(1)

			# For resistancy against security attacks
			if access_token is None:
				raise aiohttp.web.HTTPUnauthorized()

			if await authz_service.authorize(
				resources=resources,
				access_token=access_token,
				tenant=getattr(request, "Tenant", None),
			):
				return

			# Be defensive
			raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_required
