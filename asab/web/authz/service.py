import asab

import aiohttp


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)

		self.RBACUrl = asab.Config["authz"]["rbac_url"]

		self.Cache = {}

		app.PubSub.subscribe("Application.tick/60!", self._evaluate_expiration_in_cache)

	async def authorize(self, resources, access_token, tenant=None):
		# Check authorization using RBAC
		resources = ','.join(sorted(resources))

		# Obtain ID from tenant
		tenant_id = None
		if tenant is not None:
			tenant_id = tenant.Id

		# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request
		# Check that the item is located in the cache
		cache_key = "{};{}".format(tenant_id, resources)
		authorized = self._get_from_cache(cache_key)

		# Check if the authorization is cached
		if authorized is not None:
			return authorized

		async with aiohttp.ClientSession() as session:

			if tenant_id is None:
				resource_url = "{}/{}".format(self.RBACUrl, resources)
			else:
				resource_url = "{}/{}/{}".format(self.RBACUrl, tenant_id, resources)

			headers = {}
			if access_token is not None:
				headers["Authorization"] = "Bearer {}".format(access_token)

			async with session.get(
					resource_url,
					headers=headers,
			) as resp:
				authorized = resp.status == 200
				self._set_to_cache(cache_key, authorized)

				if not authorized:
					return False

		return True

	async def _evaluate_expiration_in_cache(self, event_name):
		cache_keys_to_delete = list()

		for cache_key, cache_value in self.Cache.items():
			authorized, expiration = cache_value
			if self.App.time() >= expiration:
				cache_keys_to_delete.append(cache_key)

		for cache_key in cache_keys_to_delete:
			del self.Cache[cache_key]

	def _get_from_cache(self, cache_key):
		cache_value = self.Cache.get(cache_key)
		if cache_value is None:
			return None

		return cache_value[0]

	def _set_to_cache(self, cache_key, authorized):
		self.Cache[cache_key] = (authorized, self.App.time() + 300)
