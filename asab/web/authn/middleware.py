import aiohttp

import asab
import asab.web.rest

from .oauth import oauthclient_middleware_factory


def authn_middleware(implementation, url):

	FactoryFunctions = {
		"oauth2client": oauthclient_middleware_factory
	}

	@aiohttp.web.middleware
	async def authn_middleware_factory(request, handler):
		factory_function = FactoryFunctions.get(implementation, None)
		if factory_function is None:
			raise RuntimeError("Specified implementation '{}' is not available.".format(implementation))

		return await factory_function(request, handler, url)

	return authn_middleware_factory


def authn_required_handler(func):

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['authn_identity'] = request.Identity
		except AttributeError:
			return asab.web.rest.json_response(request, {
				'result': 'IDENTITY-NOT-FOUND',
			}, status=404)
		return await func(*args, **kargs)

	return wrapper
