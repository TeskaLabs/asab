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
	Specify resources required for endpoint access.
	Requests without these resources result in HTTP 403 response.

	Args:
		resources (Iterable): Resources required to access the decorated method.

	Examples:

	```python
	@asab.web.authz.require("my-app:token:generate")
	async def generate_token(self, request):
		data = await self.service.generate_token()
		return asab.web.rest.json_response(request, data)
	```
	"""
	def decorator_require(handler):

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			authz = Authz.get()
			if authz is None:
				raise AccessDeniedError()

			if not authz.has_resource_access(resources):
				raise AccessDeniedError()

			return await handler(*args, **kwargs)

		return wrapper

	return decorator_require


def noauth(handler):
	"""
	Exempt the decorated handler from authentication and authorization.
	The `tenant`, `user_info` and `resources` arguments are not available in the handler.

	Examples:

	```python
	@asab.web.authz.noauth
	async def get_public_info(self, request):
		data = await self.service.get_public_info()
		return asab.web.rest.json_response(request, data)
	```
	"""
	argspec = inspect.getfullargspec(handler)
	args = set(argspec.kwonlyargs).union(argspec.args)
	for arg in ("tenant", "user_info", "resources"):
		if arg in args:
			raise Exception(
				"{}(): Handler with @noauth cannot have {!r} in its arguments.".format(handler.__qualname__, arg))
	handler.NoAuth = True

	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		return await handler(*args, **kwargs)

	return wrapper
