import functools

import aiohttp.web
import aiohttp.hdrs

from ...config import Config


def required(*resources):
	'''
	Checks that user authorized with access token in
	Authorization header has access to a given tenant space
	using SeaCat Auth RBAC authorization.

	It uses a cache to limit the number of HTTP checks.

	Example of use:

	@asab.web.tenant.tenant_handler
	@asab.web.authz.required("tenant:access")
	async def endpoint(self, request, *, tenant):
		...
	'''

	def decorator_required(func):

		@functools.wraps(func)
		async def wrapper(*args, **kargs):
			request = args[-1]

			# Obtain authz service from the request
			authz_service = request.AuthzService

			# Check if tenant exists in the request
			if not hasattr(request, "Tenant"):
				raise aiohttp.web.HTTPUnauthorized()

			tenant = request.Tenant
			rbac_url = Config["authz"]["rbac_url"]

			# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request

			# Check authorization using RBAC
			# Authorization header should already be part of the request
			for resource in resources:

				# Check that the item is located in the cache
				tenant_id = tenant.Id if hasattr(tenant, "Id") else tenant["_id"]
				cache_key = "{};{}".format(tenant_id, resource)
				authorized = authz_service.get_from_required_decorator_cache(cache_key)

				if authorized is not None:

					if not authorized:
						raise aiohttp.web.HTTPUnauthorized()
					else:
						continue

				async with aiohttp.ClientSession() as session:

					async with session.get(
							"{}/{}/{}".format(
								rbac_url,
								tenant_id,
								resource,
							),
							headers={
								"Authorization": request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
							}
					) as resp:

						authorized = resp.status == 200
						authz_service.set_to_required_decorator_cache(cache_key, authorized)

						if not authorized:
							raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_required
