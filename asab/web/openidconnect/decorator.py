import functools
import re

import aiohttp.web

from ...config import Config


def userinfo():
	'''
	Makes a call to OIDC userinfo endpoint and retrieves the response.

	It uses a cache to limit the number of HTTP checks.

	Example of use:
	@asab.web.tenant.tenant_handler
	@asab.web.openidconnect.userinfo
	async def endpoint(self, request, *, tenant, userinfo):
		...
	'''

	authorization_header_rg = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)")

	def decorator_userinfo(func):

		@functools.wraps(func)
		async def wrapper(*args, **kargs):

			# RBAC URL is disabled, so no authorization can be performed
			if Config["authz"]["rbac_url"] == "!DISABLED!":
				return await func(*args, **kargs)

			request = args[-1]

			# Obtain authz service from the request
			oidc_service = request.OpenIDConnectService

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

			if await oidc_service.userinfo(
				access_token=access_token,
				tenant=getattr(request, "Tenant", None),
			):
				return await func(*args, **kargs)

			# Be defensive
			raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_userinfo
