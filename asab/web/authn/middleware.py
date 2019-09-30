import aiohttp
import aiohttp.web

import asab
import asab.web.rest


def authn_middleware_factory(app, implementation, *args, **kwargs):
		
	if implementation == "oauth2client":
		from .oauth import oauthclient_middleware_factory
		return oauthclient_middleware_factory(app, *args, **kwargs)

	elif implementation == "basicauth":
		from .basicauth import basicauth_middleware_factory
		return basicauth_middleware_factory(app, *args, **kwargs)

	elif implementation == "pubkeyauth":
		from .pubkeyauth import pubkeyauth_middleware_factory
		return pubkeyauth_middleware_factory(app, *args, **kwargs)

	else:
		raise RuntimeError("Unknown authentication implementation '{}'".format(implementation))


def authn_required_handler(func):
	'''
	The web handler method require the authentication.
	The peer identity is available in the `identity` keywork argument.

	Example of use:

	@asab.web.authn.authn_required_handler
	async def endpoint(self, request, *, identity):
		...
	'''

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['identity'] = request.Identity
		except AttributeError:
			raise aiohttp.web.HTTPUnauthorized()
		return await func(*args, **kargs)

	return wrapper


def authn_optional_handler(func):
	'''
	The web handler method request the OPTINAL authentication.
	The peer identity is available in the `identity` keywork argument.
	`identity` is None if the peer has not provided authentication info.

	Example of use:

	@asab.web.authn.authn_optional_handler
	async def endpoint(self, request, *, identity):
		...
	'''

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['identity'] = request.Identity
		except AttributeError:
			kargs['identity'] = None
		return await func(*args, **kargs)

	return wrapper
