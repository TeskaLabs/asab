import logging
import functools
import inspect

from ...exceptions import AccessDeniedError
from ...contextvars import Authz

#

L = logging.getLogger(__name__)

#


def require(*resources):
	"""
	Require that the request have authorized access to one or more resources.
	Requests without these resources result in AccessDeniedError and consequently in an HTTP 403 response.

	Args:
		resources (Iterable): Resources whose authorization is required.

	Examples:

	```python
	@asab.web.auth.require("insider-info:access")
	async def get_insider_info(self, request):
		data = await self.service.get_insider_info()
		return asab.web.rest.json_response(request, data)
	```
	"""
	def _require_resource_access_decorator(handler):

		@functools.wraps(handler)
		async def _require_resource_access_wrapper(*args, **kwargs):
			authz = Authz.get()
			if authz is None:
				raise AccessDeniedError()

			authz.require_resource_access(*resources)

			return await handler(*args, **kwargs)

		return _require_resource_access_wrapper

	return _require_resource_access_decorator


def require_superuser(handler):
	"""
	Require that the request have authorized access to the superuser resource.
	Requests without superuser access result in AccessDeniedError and consequently in an HTTP 403 response.

	Examples:

	```python
	@asab.web.auth.require_superuser
	async def get_confidential_info(self, request):
		data = await self.service.get_confidential_info()
		return asab.web.rest.json_response(request, data)
	```
	"""
	@functools.wraps(handler)
	async def _require_superuser_access_wrapper(*args, **kwargs):
		authz = Authz.get()
		if authz is None:
			raise AccessDeniedError()

		authz.require_superuser_access()

		return await handler(*args, **kwargs)

	return _require_superuser_access_wrapper


def noauth(handler):
	"""
	Exempt the decorated handler from authentication and authorization.

	Examples:

	```python
	@asab.web.auth.noauth
	async def get_public_info(self, request):
		data = await self.service.get_public_info()
		return asab.web.rest.json_response(request, data)
	```
	"""
	argspec = inspect.getfullargspec(handler)
	args = set(argspec.kwonlyargs).union(argspec.args)
	for arg in ("user_info", "resources", "authz"):
		if arg in args:
			raise Exception(
				"{}(): Handler with @noauth cannot have {!r} in its arguments.".format(handler.__qualname__, arg))
	handler.NoAuth = True

	@functools.wraps(handler)
	async def _noauth_wrapper(*args, **kwargs):
		return await handler(*args, **kwargs)

	return _noauth_wrapper
