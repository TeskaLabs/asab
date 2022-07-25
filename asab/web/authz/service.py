import hashlib
import aiohttp

import asab
import logging

#

L = logging.getLogger(__name__)

#


asab.Config.add_defaults({
	"authz": {
		"oauth2_url": "",
		"userinfo_endpoint": "/userinfo",
		"cache_expiration": "1 m"
	}
})


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)

		self.OAuth2Url = asab.Config.get("authz", "oauth2_url")
		if self.OAuth2Url.endswith("/"):
			self.OAuth2Url = self.OAuth2Url[:-1]

		self.UserInfoEndpoint = asab.Config.get("authz", "userinfo_endpoint")
		self.CacheExpiration = asab.Config.getseconds("authz", "cache_expiration")

		self.Cache = {}

		app.PubSub.subscribe("Application.tick/60!", self._evaluate_expiration_in_cache)

	async def authorize(self, resources, access_token, tenant=None):
		# Use userinfo to make RBAC check
		userinfo = await self.userinfo(access_token)

		# Fail if userinfo cannot be fetched or resources are missing
		if userinfo is None:
			return False
		user_resources = userinfo.get("resources")
		if not isinstance(user_resources, dict):
			# TODO: Backward compatibility. Remove after Dec 2022
			user_resources = userinfo.get("authz")
		if user_resources is None:
			return False

		# Allow superuser to pass any check
		if "authz:superuser" in frozenset(user_resources.get("*", [])):
			return True

		if tenant is None:
			# Check only global resources if no tenant is specified
			tenant = "*"
		if tenant not in user_resources:
			# Tenant section is not present: The check has failed
			return False

		# Make sure all the required resources are accessible
		tenant_user_resources = frozenset(user_resources[tenant])
		for resource in resources:
			if resource == "tenant:access":
				# Tenant section is present: User has tenant access
				continue
			if resource not in tenant_user_resources:
				return False

		return True

	async def userinfo(self, access_token):
		# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request
		# Check that the item is located in the cache
		userinfo = self._get_from_cache(access_token)

		# Check if the authorization is cached
		if userinfo is not None:
			return userinfo

		async with aiohttp.ClientSession() as session:
			userinfo_url = "{}{}".format(self.OAuth2Url, self.UserInfoEndpoint)

			headers = {}
			if access_token is not None:
				headers["Authorization"] = "Bearer {}".format(access_token)

			async with session.get(
				userinfo_url,
				headers=headers,
			) as response:
				if response.status != 200:
					L.error("Failed to fetch userinfo", struct_data={
						"status": response.status,
						**dict(response.headers),
					})
					return None

				response_json = await response.json()
				if len(response_json) > 0:
					userinfo = response_json

				self._set_to_cache(access_token, userinfo)

		return userinfo

	async def _evaluate_expiration_in_cache(self, event_name):
		cache_keys_to_delete = list()

		for cache_key, cache_value in self.Cache.items():
			authorized, expiration = cache_value
			if self.App.time() >= expiration:
				cache_keys_to_delete.append(cache_key)

		for cache_key in cache_keys_to_delete:
			del self.Cache[cache_key]

	def _get_from_cache(self, access_token):
		key = access_token.encode("utf-8")
		hashed = hashlib.sha256(key).digest()
		cache_value = self.Cache.get(hashed)
		if cache_value is None:
			return None

		return cache_value[0]

	def _set_to_cache(self, access_token, userinfo):
		key = access_token.encode("utf-8")
		hashed = hashlib.sha256(key).digest()
		self.Cache[hashed] = (userinfo, self.App.time() + self.CacheExpiration)
