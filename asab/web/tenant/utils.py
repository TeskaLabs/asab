import inspect
import functools
import aiohttp.web

from ...contextvars import Tenant


async def set_up_tenant_web_wrapper(aiohttp_app: aiohttp.web.Application):
	"""
	Inspect all registered handlers and wrap them in decorators according to their parameters.
	"""
	for route in aiohttp_app.router.routes():
		# Skip non-coroutines
		if not inspect.iscoroutinefunction(route.handler):
			continue

		# Skip HEAD requests
		if route.method == "HEAD":
			continue

		try:
			_set_handler_tenant(route)
		except Exception as e:
			raise Exception(
				"Failed to initialize tenant context for handler {!r}.".format(route.handler.__qualname__)
			) from e


def _set_handler_tenant(route: aiohttp.web.AbstractRoute):
	"""
	Inspect handler and apply suitable auth wrappers.
	"""
	# Extract the whole handler including its existing decorators and wrappers
	handler = route.handler

	# Apply the decorators IN REVERSE ORDER (the last applied wrapper affects the request first)

	# 2) Pass tenant if it is in handler args
	if "tenant" in _get_route_handler_args(route):
		handler = _pass_tenant(handler)

	# 1) Set tenant context from URL path or query
	route_info = route.get_info()
	if "formatter" in route_info and "{tenant}" in route_info["formatter"]:
		handler = _set_tenant_context_from_url_path(handler)
	else:
		handler = _set_tenant_context_from_url_query(handler)

	route._handler = handler


def _pass_tenant(handler):
	"""
	Add tenant to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		return await handler(*args, tenant=Tenant.get(), **kwargs)
	return wrapper


def _set_tenant_context_from_url_query(handler):
	"""
	Extract tenant from request query and add it to context
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		tenant = request.query.get("tenant")

		if tenant is None and not (
			hasattr(handler, "AllowNoTenant") and handler.AllowNoTenant is True
		):
			# TODO: Use asab.exceptions.ValidationError instead once it implements aiohttp.web.HTTPBadRequest
			raise aiohttp.web.HTTPBadRequest(reason="Missing `tenant` parameter in URL query.")

		tenant_ctx = Tenant.set(tenant)
		try:
			response = await handler(*args, **kwargs)
		finally:
			Tenant.reset(tenant_ctx)

		return response

	return wrapper


def _set_tenant_context_from_url_path(handler):
	"""
	Extract tenant from request URL path and add it to context
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		tenant = request.match_info["tenant"]

		tenant_ctx = Tenant.set(tenant)
		try:
			response = await handler(*args, **kwargs)
		finally:
			Tenant.reset(tenant_ctx)

		return response

	return wrapper


def _get_route_handler_args(route):
	# Extract the actual unwrapped handler method for signature inspection
	handler_method = route.handler
	while hasattr(handler_method, "__wrapped__"):
		# While loop unwraps handlers wrapped in multiple decorators.
		# NOTE: This requires all the decorators to use @functools.wraps().
		handler_method = handler_method.__wrapped__
	if hasattr(handler_method, "__func__"):
		handler_method = handler_method.__func__
	argspec = inspect.getfullargspec(handler_method)
	args = set(argspec.kwonlyargs).union(argspec.args)
	return args
