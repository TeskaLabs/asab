import inspect
import logging
import functools
import aiohttp.web

from ...contextvars import Tenant

#

L = logging.getLogger(__name__)
NO_TENANT_ROUTES = set()

#


class TenantWebWrapperInstaller:
	"""
	Wraps web handlers with middleware that extracts tenant from URL path or query and sets tenant context
	"""

	def __init__(self, tenant_service, strict: bool = True):
		self.TenantService = tenant_service
		self.Strict = strict


	def __call__(self, aiohttp_app: aiohttp.web.Application):
		"""
		Inspect all registered handlers and wrap them in decorators according to their parameters.
		"""
		for route in aiohttp_app.router.routes():
			# Skip non-coroutines
			if not inspect.iscoroutinefunction(route.handler):
				continue

			try:
				self.set_handler_tenant(route, strict=self.Strict)
			except Exception as e:
				raise RuntimeError(
					"Failed to initialize tenant context for handler {!r}: {}".format(route.handler.__qualname__, e)
				) from e


	def set_handler_tenant(self, route: aiohttp.web.AbstractRoute, strict: bool):
		"""
		Inspect handler and apply suitable tenant wrappers.
		"""
		# Extract the whole handler including its existing decorators and wrappers
		handler = route.handler
		route_info = route.get_info()

		if "path" in route_info:
			path = route_info["path"]
		elif "formatter" in route_info:
			path = route_info["formatter"]
		else:
			raise RuntimeError("Route has no path or formatter: {}".format(route_info))

		# If the route is in NO_TENANT_ROUTES, skip tenant handling
		if path in NO_TENANT_ROUTES:
			return

		# Apply the decorators IN REVERSE ORDER (the last applied wrapper affects the request first)

		# 2) Pass tenant if it is in handler args
		if "tenant" in _get_route_handler_args(route):
			handler = self._pass_tenant(handler)

		# 1) Set tenant context from URL path or query
		if strict:
			if not ("formatter" in route_info and route_info["formatter"].startswith("/{tenant}")):
				raise RuntimeError("In strict mode, all endpoint paths must start with `/{tenant}`.")
			if hasattr(handler, "AllowNoTenant") and handler.AllowNoTenant is True:
				raise RuntimeError("In strict mode, the use of @allow_no_tenant is not permitted.")
		else:
			if "formatter" in route_info and route_info["formatter"].startswith("/{tenant}"):
				raise RuntimeError("In non-strict mode, endpoint paths must NOT start with `/{tenant}`.")

		if "formatter" in route_info and "{tenant}" in route_info["formatter"]:
			handler = self._set_tenant_context_from_url_path(handler)
		else:
			handler = self._set_tenant_context_from_url_query(handler)

		route._handler = handler


	def _pass_tenant(self, handler):
		"""
		Pass tenant from Tenant context variable to web handler as an argument.
		"""
		@functools.wraps(handler)
		async def _pass_tenant_wrapper(*args, **kwargs):
			tenant = Tenant.get()

			if tenant is None:
				if not (hasattr(handler, "AllowNoTenant") and handler.AllowNoTenant is True):
					raise aiohttp.web.HTTPNotFound(reason="Tenant not found.")
				else:
					# `None` is allowed: Tenant is optional at this endpoint.
					pass

			elif not await self.TenantService.is_tenant_known(tenant):
				L.warning("Tenant not found.", struct_data={"tenant": tenant})
				raise aiohttp.web.HTTPNotFound(reason="Tenant not found.")
			return await handler(*args, tenant=tenant, **kwargs)
		return _pass_tenant_wrapper


	def _set_tenant_context_from_url_query(self, handler):
		"""
		Extract tenant from request query and add it to context
		"""
		@functools.wraps(handler)
		async def _tenant_context_from_url_query_wrapper(*args, **kwargs):
			request = args[-1]
			tenant = request.query.get("tenant")

			if tenant is None:
				if not (hasattr(handler, "AllowNoTenant") and handler.AllowNoTenant is True):
					L.warning("URL contains no `tenant` parameter.")
					raise aiohttp.web.HTTPNotFound(reason="Tenant not found.")
				else:
					# `None` is allowed: Tenant is optional at this endpoint.
					pass

			elif not await self.TenantService.is_tenant_known(tenant):
				L.warning("Tenant not found.", struct_data={"tenant": tenant})
				raise aiohttp.web.HTTPNotFound(reason="Tenant not found.")

			tenant_ctx = Tenant.set(tenant)
			try:
				response = await handler(*args, **kwargs)
			finally:
				Tenant.reset(tenant_ctx)

			return response

		return _tenant_context_from_url_query_wrapper


	def _set_tenant_context_from_url_path(self, handler):
		"""
		Extract tenant from request URL path and add it to context
		"""
		@functools.wraps(handler)
		async def _tenant_context_from_url_path_wrapper(*args, **kwargs):
			request = args[-1]
			tenant = request.match_info["tenant"]

			if "tenant" in request.query:
				L.warning("Parameter `tenant` cannot be present in URL path and query at the same time.")
				raise aiohttp.web.HTTPBadRequest(reason="Tenant query parameter not allowed.")

			if not await self.TenantService.is_tenant_known(tenant):
				L.warning("Tenant not found.", struct_data={"tenant": tenant})
				raise aiohttp.web.HTTPNotFound(reason="Tenant not found.")

			tenant_ctx = Tenant.set(tenant)
			try:
				response = await handler(*args, **kwargs)
			finally:
				Tenant.reset(tenant_ctx)

			return response

		return _tenant_context_from_url_path_wrapper


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
