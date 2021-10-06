import hashlib
import aiohttp

import asab


asab.Config.add_defaults({
	"authz": {
		"userinfo_url": "",
		"cache_expiration": "1 m"
	}
})


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)

		self.UserInfoUrl = asab.Config.get("authz", "userinfo_url")
		self.CacheExpiration = asab.Config.getseconds("authz", "cache_expiration")

		self.Cache = {}

		app.PubSub.subscribe("Application.tick/60!", self._evaluate_expiration_in_cache)

	async def authorize(self, resources, access_token, tenant=None):
		# Use userinfo to make RBAC check
		userinfo = await self.userinfo(access_token, tenant)

		# Fail if userinfo cannot be fetched or resources are missing
		if userinfo is None:
			return False
		accessible_resources = userinfo.get("resources")
		if accessible_resources is None:
			return False

		# Allow superuser to pass any check
		if "authz:superuser" in accessible_resources:
			return True

		# Make sure all the required resources are accessible
		for resource in resources:
			if resource not in accessible_resources:
				return False

		return True

	async def userinfo(self, access_token, tenant=None):
		# Obtain ID from tenant
		tenant_id = None
		if tenant is not None:
			tenant_id = tenant.Id

		# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request
		# Check that the item is located in the cache
		userinfo = self._get_from_cache(access_token, tenant_id)

		# Check if the authorization is cached
		if userinfo is not None:
			return userinfo

		async with aiohttp.ClientSession() as session:
			if tenant_id is not None:
				userinfo_url = "{}?tenant={}".format(self.UserInfoUrl, tenant_id)
			else:
				userinfo_url = self.UserInfoUrl

			headers = {}
			if access_token is not None:
				headers["Authorization"] = "Bearer {}".format(access_token)

			async with session.get(
					userinfo_url,
					headers=headers,
			) as response:
				if response.status == 200:
					response_json = await response.json()
					if len(response_json) > 0:
						userinfo = response_json

				self._set_to_cache(access_token, tenant_id, userinfo)

		return userinfo

	async def _evaluate_expiration_in_cache(self, event_name):
		cache_keys_to_delete = list()

		for cache_key, cache_value in self.Cache.items():
			authorized, expiration = cache_value
			if self.App.time() >= expiration:
				cache_keys_to_delete.append(cache_key)

		for cache_key in cache_keys_to_delete:
			del self.Cache[cache_key]

	def _get_from_cache(self, access_token, tenant_id):
		key = "{} {}".format(access_token, tenant_id).encode("utf-8")
		hashed = hashlib.sha256(key).digest()
		cache_value = self.Cache.get(hashed)
		if cache_value is None:
			return None

		return cache_value[0]

	def _set_to_cache(self, access_token, tenant_id, userinfo):
		key = "{} {}".format(access_token, tenant_id).encode("utf-8")
		hashed = hashlib.sha256(key).digest()
		self.Cache[hashed] = (userinfo, self.App.time() + self.CacheExpiration)
