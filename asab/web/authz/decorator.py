import re
import logging
import functools
import inspect

import aiohttp.web

#

L = logging.getLogger(__name__)

#


def require(*resources):

	def decorator_required(handler):

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]

			for resource in resources:
				if not request.has_resource_access(resource):
					raise aiohttp.web.HTTPForbidden()

			return await handler(*args, **kwargs)

		return wrapper

	return decorator_required


def no_auth(handler):
	argspec = inspect.getfullargspec(handler)
	args = set(argspec.kwonlyargs).union(argspec.args)
	for arg in ("tenant", "user_info", "resources"):
		if arg in args:
			raise Exception(
				"{}(): Handler with @no_auth cannot have {!r} in its arguments.".format(handler.__qualname__, arg))
	handler.NoAuth = True

	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		return await handler(*args, **kwargs)

	return wrapper


def _get_bearer_token(request):
	authorization_header_rg = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)")

	authorization_value = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
	bearer_token = None

	# Obtain access token from the authorization header
	if authorization_value is not None:
		authorization_match = authorization_header_rg.match(authorization_value)
		if authorization_match is not None:
			bearer_token = authorization_match.group(1)

	return bearer_token
