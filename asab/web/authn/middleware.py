import aiohttp

import asab
import asab.web.rest


def authn_middleware_factory(app, implementation, *args, **kwargs):
		
	if implementation == "oauth2client":
		from .oauth import oauthclient_middleware_factory
		return oauthclient_middleware_factory(app, *args, **kwargs)

	elif implementation == "basicauth":
		from .basicauth import basicauth_middleware_factory
		return basicauth_middleware_factory(app, *args, **kwargs)

	elif factory_function is None:
		raise RuntimeError("Unknown authentication implementation '{}'".format(implementation))


def authn_required_handler(func):

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['identity'] = request.Identity
		except AttributeError:
			return asab.web.rest.json_response(request, {
				'result': 'AUTHENTICATION-REQUIRED',
			}, status=401)
		return await func(*args, **kargs)

	return wrapper


def authn_optional_handler(func):

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['identity'] = request.Identity
		except AttributeError:
			kargs['identity'] = None
		return await func(*args, **kargs)

	return wrapper
