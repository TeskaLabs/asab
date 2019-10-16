import time
import logging

import aiohttp

#

L = logging.getLogger(__name__)

#


class OAuthIdentityCache(object):
	"""
	OAuthIdentityCache serves to store and periodically refresh OAuth identities obtained from the OAuth server
	specified in the methods list.

	:methods is a list that specifies the identification of OAuth servers such as [asab.web.authn.oauth.GitHubOAuthMethod()]
	:identity_cache_longevity is an integer that specifies the number of seconds after which the cached identity expires
	"""

	def __init__(self, app, methods, identity_cache_longevity=60*60):
		# Prepare empty cache
		self.IdentityCache = {}
		self.IdentityCacheLongevity = identity_cache_longevity

		# Load methods
		self.MethodsDict = {}
		for method in methods:
			self.MethodsDict[method.Config["oauth_server_id"]] = method

		# Subscribe to periodically refresh cache
		app.PubSub.subscribe("Application.tick/10!", self._refresh)

	def get_methods(self):
		return self.MethodsDict

	def get_identity(self, oauth_server_id_access_token):
		return self.IdentityCache.get(oauth_server_id_access_token)

	def insert_identity(self, oauth_server_id_access_token, oauth_user_info, identity):
		expiration = time.time() + self.IdentityCacheLongevity
		self.IdentityCache[oauth_server_id_access_token] = {
			"OAuthUserInfo": oauth_user_info,
			"Identity": identity,
			"Expiration": expiration,
		}

	def delete_identity(self, oauth_server_id_access_token):
		if oauth_server_id_access_token in self.IdentityCache:
			del self.IdentityCache[oauth_server_id_access_token]
			return True
		return False

	async def _refresh(self, message_type):
		current_time = time.time()
		for oauth_server_id_access_token, identity in self.IdentityCache.items():
			expiration = identity.get("Expiration", time.time())

			# Refresh expired cache items
			if expiration <= current_time:

				oauth_server_id, access_token = oauth_server_id_access_token.split('-', 1)
				method = self.MethodsDict.get(oauth_server_id)

				assert method is not None

				oauth_userinfo_url = method.Config["identity_url"]
				async with aiohttp.ClientSession() as session:
					async with session.get(oauth_userinfo_url,
										   headers={"Authorization": "Bearer {}".format(access_token)}) as resp:
						if resp.status == 200:
							oauth_user_info = await resp.json()
							if oauth_user_info is not None:
								self.insert_identity(oauth_server_id_access_token, oauth_user_info, method.extract_identity(
									oauth_user_info
								))
						else:
							# If there was an error, remove the cache item
							L.warn("Identity '{}' could not be refreshed on ''.".format(identity, oauth_userinfo_url))
							self.delete_identity(oauth_server_id_access_token)
