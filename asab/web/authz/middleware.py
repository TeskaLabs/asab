import aiohttp.web
import logging

#

L = logging.getLogger(__name__)

#


def auth_middleware_factory(authz_service):

	@aiohttp.web.middleware
	async def auth_middleware(request, handler):
		# Handlers with the @no_auth decorator are not authenticated nor authorized
		# and do not have access to tenant or userinfo
		if hasattr(handler, "NoAuth"):
			return await handler(request)

		if not authz_service.is_ready():
			L.error("Cannot authorize request: AuthzService is not ready.")
			raise aiohttp.web.HTTPUnauthorized()
		request.AuthzService = authz_service

		# Extract tenant from request
		request._Tenant = request.match_info.get("tenant")
		if request._Tenant is None:
			request._Tenant = request.query.get("tenant")

		# Authenticate the request
		bearer_token = _get_bearer_token(request)
		request._UserInfo = authz_service.userinfo(bearer_token)

		resource_dict = request._UserInfo.get("resources")

		# Extract globally-granted resources
		request._Resources = frozenset(resource_dict["*"])
		request.is_superuser = "authz:superuser" in request._Resources

		# Authorize tenant access
		if request._Tenant is not None:
			if request._Tenant in resource_dict:
				# Extract tenant-granted resources
				request._Resources = frozenset(resource_dict[request._Tenant])
			elif request.is_superuser:
				# Superuser may proceed with globally-granted resources
				pass
			else:
				L.warning("Unauthorized tenant access", struct_data={
					"tenant": request._Tenant, "sub": request._UserInfo.get("sub")})
				raise aiohttp.web.HTTPForbidden()

		def has_resource_access(resource: str) -> bool:
			return request.is_superuser or resource in request._Resources

		request.has_resource_access = has_resource_access

		return await handler(request, tenant=request._Tenant, user_info=request._UserInfo, resources=request._Resources)

	return auth_middleware


def _get_bearer_token(request):
	authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
	if authorization_header is None:
		L.warning("No Authorization header")
		raise aiohttp.web.HTTPUnauthorized()
	try:
		auth_type, token_value = authorization_header.split(" ", 1)
	except ValueError:
		L.warning("Invalid Authorization header")
		raise aiohttp.web.HTTPUnauthorized()
	if auth_type != "Bearer":
		L.warning("Unsupported Authorization header type: {!r}".format(auth_type))
		raise aiohttp.web.HTTPUnauthorized()
	return token_value
