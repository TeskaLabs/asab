import aiohttp.web
import logging
import inspect

#

L = logging.getLogger(__name__)

#


def auth_middleware_factory(authz_service, web_app):
	async def extract_auth_attributes(aiohttp_app):
		for route in aiohttp_app.router.routes():
			if inspect.iscoroutinefunction(route.handler):
				if hasattr(route.handler, "__wrapped__"):
					handler = route.handler.__wrapped__
				else:
					handler = route.handler.__func__
				argspec = inspect.getfullargspec(handler)
				args = set(argspec.kwonlyargs).union(argspec.args)
				if "tenant" in args:
					handler.Tenant = True
				if "user_info" in args:
					handler.UserInfo = True
				if "resources" in args:
					handler.Resources = True

	web_app.on_startup.append(extract_auth_attributes)

	@aiohttp.web.middleware
	async def auth_middleware(request, handler):
		# Handlers with the @no_auth decorator are not authenticated nor authorized
		# and do not have access to tenant or user_info
		if hasattr(handler, "NoAuth"):
			return await handler(request)

		if not authz_service.is_ready():
			L.error("Cannot authorize request: AuthzService is not ready.")
			raise aiohttp.web.HTTPUnauthorized()
		request.AuthzService = authz_service

		# Extract tenant from request
		tenant = request.match_info.get("tenant")
		if tenant is None:
			tenant = request.query.get("tenant")

		# Authenticate the request
		bearer_token = _get_bearer_token(request)
		user_info = authz_service.userinfo(bearer_token)

		resource_dict = user_info.get("resources")

		# Extract globally-granted resources
		resources = frozenset(resource_dict["*"])
		request.is_superuser = "authz:superuser" in resources

		# Authorize tenant access
		if tenant is not None:
			if tenant in resource_dict:
				# Extract tenant-granted resources
				resources = frozenset(resource_dict[tenant])
			else:
				L.warning("Unauthorized tenant access", struct_data={
					"tenant": tenant, "sub": user_info.get("sub")})
				raise aiohttp.web.HTTPUnauthorized()

		def has_resource_access(resource: str) -> bool:
			return request.is_superuser or resource in resources

		request.has_resource_access = has_resource_access

		kwargs = {}
		if hasattr(handler, "Tenant"):
			kwargs["tenant"] = tenant
		if hasattr(handler, "Resources"):
			kwargs["resources"] = resources
		if hasattr(handler, "UserInfo"):
			kwargs["user_info"] = user_info

		return await handler(request, **kwargs)

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
