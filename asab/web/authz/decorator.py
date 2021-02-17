import aiohttp.web
import aiohttp.hdrs

from ...config import Config


def authz_rbac_tenant(func):
	'''
	Checks that user authorized with access token in
	Authorization header has access to a given tenant space
	using SeaCat Auth RBAC authorization.

	Example of use:

	@asab.web.tenant.tenant_handler
	@asab.web.authz.authz_rbac_tenant
	async def endpoint(self, request, *, tenant):
		...
	'''

	async def wrapper(*args, **kargs):
		request = args[-1]

		# Check if tenant exists in the request
		if not hasattr(request, "Tenant"):
			raise aiohttp.web.HTTPUnauthorized()

		tenant = request.Tenant
		rbac_url = Config["authz"]["rbac_url"]

		# Check authorization using RBAC
		# Authorization header should already be part of the request
		async with aiohttp.ClientSession() as session:

			async with session.get(
					"{}/{}/tenant:access".format(
						rbac_url,
						tenant.Id if hasattr(tenant, "Id") else tenant["_id"]
					),
					headers={
						"Authorization": request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
					}
			) as resp:
				if resp.status != 200:
					raise aiohttp.web.HTTPUnauthorized()

		return await func(*args, **kargs)

	return wrapper
