import functools
import time

import aiohttp.web
import aiohttp.hdrs

from ...config import Config

required_cache_dict = dict()


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

			# Check if tenant exists in the request
			if not hasattr(request, "Tenant"):
				raise aiohttp.web.HTTPUnauthorized()

			tenant = request.Tenant
			rbac_url = Config["authz"]["rbac_url"]

			current_time = time.time()

			# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request
			cache_keys_to_delete = list()

			for cache_key, cache_value in required_cache_dict.items():
				authorized, expiration = cache_value
				if current_time >= expiration:
					cache_keys_to_delete.append(cache_key)

			for cache_key in cache_keys_to_delete:
				del required_cache_dict[cache_key]

			# Check authorization using RBAC
			# Authorization header should already be part of the request
			for resource in resources:

				# Check that the item is located in the cache
				tenant_id = tenant.Id if hasattr(tenant, "Id") else tenant["_id"]
				cache_key = "{};{}".format(tenant_id, resource)
				cache_value = required_cache_dict.get(cache_key)

				if cache_value is not None:
					authorized, expiration = cache_value

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
						required_cache_dict[cache_key] = (authorized, current_time + 300)

						if not authorized:
							raise aiohttp.web.HTTPUnauthorized()

		return wrapper

	return decorator_required
