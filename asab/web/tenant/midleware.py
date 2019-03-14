import aiohttp.web

import asab
import asab.web.rest


def tenant_middleware_factory(app, svc):

	@aiohttp.web.middleware
	async def tenant_middleware(request, handler):
		tenant_id = request.match_info.get('tenant')
		if tenant_id is not None:
			tenant = svc.locate_tenant(tenant_id)
			if tenant is not None:
				request.Tenant = tenant
		return await handler(request)

	return tenant_middleware


def tenant_handler(func):

	async def wrapper(*args, **kargs):
		request = args[-1]
		try:
			kargs['tenant'] = request.Tenant
		except AttributeError:
			return asab.web.rest.json_response(request, {
				'result': 'TENANT-NOT-FOUND',
			}, status=404)
		return await func(*args, **kargs)

	return wrapper
