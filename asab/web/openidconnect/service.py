import asab

import aiohttp
import hashlib


asab.Config.add_defaults({
	"openidconnect": {
		"url": "",  # E.g. "http://seacat-auth:8080/openidconnect"
		"cache_expiration": "5 m"  # How long is userinfo response cached
	}
})


class OpenIDConnectService(asab.Service):

	def __init__(self, app, service_name="asab.OpenIDConnectService"):
		super().__init__(app, service_name)

		self.OIDCUrl = asab.Config.get("openidconnect", "url")
		self.CacheExpiration = asab.Config.getseconds("openidconnect", "cache_expiration")

		self.UserinfoCache = {}

		app.PubSub.subscribe("Application.tick/60!", self._evaluate_expiration_in_cache)

	async def userinfo(self, access_token, tenant=None):
		# Obtain ID from tenant
		tenant_id = None
		if tenant is not None:
			tenant_id = tenant.Id

		# TODO: Replace cache invalidation with more clever approach like session indicator in the HTTP request
		# Check that the item is located in the cache
		response = self._get_from_cache(access_token, tenant_id)

		# Check if the authorization is cached
		if response is not None:
			return response

		async with aiohttp.ClientSession() as session:
			if tenant_id is not None:
				userinfo_url = "{}/userinfo".format(self.OIDCUrl)
			else:
				userinfo_url = "{}/userinfo?tenant={}".format(self.OIDCUrl, tenant_id)

			headers = {}
			if access_token is not None:
				headers["Authorization"] = "Bearer {}".format(access_token)

			async with session.get(
					userinfo_url,
					headers=headers,
			) as response:
				userinfo = None

				if response.status == 200:
					response_json = await response.json()

					if len(response_json) > 0:
						userinfo = response_json

				self._set_to_cache(access_token, tenant_id, response)

		# Be pessimistic
		return userinfo

	async def _evaluate_expiration_in_cache(self, event_name):
		cache_keys_to_delete = list()

		for cache_key, cache_value in self.UserinfoCache.items():
			authorized, expiration = cache_value
			if self.App.time() >= expiration:
				cache_keys_to_delete.append(cache_key)

		for cache_key in cache_keys_to_delete:
			del self.UserinfoCache[cache_key]

	def _get_from_cache(self, access_token, tenant_id):
		key = "{} {}".format(access_token, tenant_id)
		hashed = hashlib.sha256(key).digest()
		cache_value = self.UserinfoCache.get(hashed)
		if cache_value is None:
			return None

		return cache_value[0]

	def _set_to_cache(self, access_token, tenant_id, userinfo):
		key = "{} {}".format(access_token, tenant_id)
		hashed = hashlib.sha256(key).digest()
		self.UserinfoCache[hashed] = (userinfo, self.App.time() + self.CacheExpiration)
