import re
import logging
import functools

import aiohttp.web

#

L = logging.getLogger(__name__)

#


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

			# RBAC URL is disabled, so no authorization can be performed
			if request.AuthzService.OAuth2Url == "!DISABLED!":
				return await func(*args, **kargs)

			elif request.AuthzService.OAuth2Url == "":
				L.error("oauth2_url is not configured ;-(")
				raise aiohttp.web.HTTPUnauthorized()

			access_token = _get_access_token(request)

			# For resistancy against security attacks
			if access_token is None:
				raise aiohttp.web.HTTPUnauthorized()

			if await authz_service.authorize(
				resources=resources,
				access_token=access_token,
				tenant=getattr(request, "Tenant", None),
			):
				return await func(*args, **kargs)

			# Be defensive
			raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_required


def userinfo_handler(func):
	"""
	Fetches userinfo and passes the response dict to the decorated function.

	It uses a cache to limit the number of HTTP checks.

	Example of use:

	@asab.web.tenant.tenant_handler
	@asab.web.authz.userinfo
	async def endpoint(self, request, *, tenant, userinfo):
		...
	"""

	@functools.wraps(func)
	async def wrapper(*args, **kargs):
		request = args[-1]

		# Obtain authz service from the request
		authz_service = request.AuthzService

		# RBAC URL is disabled, so no authorization can be performed
		if request.AuthzService.OAuth2Url == "!DISABLED!":
			return await func(*args, **kargs)

		elif request.AuthzService.OAuth2Url == "":
			L.error("oauth2_url is not configured ;-(")
			raise aiohttp.web.HTTPUnauthorized()

		access_token = _get_access_token(request)

		# Fail if no access token is found in the request
		if access_token is None:
			L.warning("Access token has not been provided in the request - unauthorized.")
			raise aiohttp.web.HTTPUnauthorized()

		userinfo_data = await authz_service.userinfo(access_token=access_token)
		if userinfo_data is not None:
			return await func(*args, userinfo=userinfo_data, **kargs)

		# Be defensive
		L.warning("Failure to get userinfo  - unauthorized.")
		raise aiohttp.web.HTTPUnauthorized()

	return wrapper


def _get_access_token(request):
	authorization_header_rg = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)")

	authorization_value = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
	access_token = None

	# Obtain access token from the authorization header
	if authorization_value is not None:
		authorization_match = authorization_header_rg.match(authorization_value)
		if authorization_match is not None:
			access_token = authorization_match.group(1)

	return access_token
