import logging
import functools
import inspect

import asab.exceptions

#

L = logging.getLogger(__name__)

#


def require(*resources):
	"""
	Check resource access. Failure results in HTTP 403 response.

	Usage:
	```python3
	@asab.web.authz.require("my-app:token:generate")
	async def generate_token(self, request):
		data = await self.service.generate_token()
		return asab.web.rest.json_response(request, data)
	```
	"""
	def decorator_require(handler):

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]

			if not hasattr(request, "has_resource_access"):
				raise Exception(
					"Cannot check resource access. Make sure the handler method does not use "
					"both the @noauth and the @require decorators.")

			if not request.has_resource_access(*resources):
				raise asab.exceptions.AccessDeniedError()

			return await handler(*args, **kwargs)

		return wrapper

	return decorator_require


def noauth(handler):
	"""
	Skip request authentication and authorization for the decorated handler.
	The handler cannot have `tenant`, `user_info` and `resources` arguments.

	Usage:
	```python3
	@asab.web.authz.noauth
	async def get_info(self, request):
		data = await self.service.get_info()
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
