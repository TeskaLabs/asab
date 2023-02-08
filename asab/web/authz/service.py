import json
import logging
import aiohttp

import jwcrypto.jwk
import jwcrypto.jwt
import jwcrypto.jws

import asab
import asab.exceptions

#

L = logging.getLogger(__name__)

#


asab.Config.add_defaults({
	"authz": {
		"public_keys_url": "",  # If no public keys url is provided, ID tokens are not validated
		"cache_expiration": "1 m"
	}
})


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)
		self.PublicKeysUrl = asab.Config.get("authz", "public_keys_url")
		self.PublicKey = None

	async def initialize(self, app):
		if self.PublicKeysUrl is not None:
			# TODO: Retry if unsuccessful
			await self.get_public_keys()

	async def get_public_keys(self):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.PublicKeysUrl) as response:
				if response.status != 200:
					L.error("Cannot retrieve public keys from authorization server", struct_data={
						"status": response.status,
						"url": self.PublicKeysUrl,
						"text": await response.text(),
					})
					raise ConnectionError()

				jwkeys = await response.json()
				self.PublicKey = jwcrypto.jwk.JWK(**jwkeys.pop())

	async def authorize(self, resources, bearer_token, tenant=None):
		# Use userinfo to make RBAC check
		userinfo = await self.userinfo(bearer_token)

		# Fail if userinfo cannot be fetched or resources are missing
		if userinfo is None:
			return False
		user_resources = userinfo.get("resources")
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

	async def userinfo(self, bearer_token):
		return self._get_id_token_claims(bearer_token)

	def _get_id_token_claims(self, bearer_token):
		# TODO: Don't check signature if no public key url is provided
		try:
			token = jwcrypto.jwt.JWT(jwt=bearer_token, key=self.PublicKey)
		except jwcrypto.jwt.JWTExpired:
			raise asab.exceptions.NotAuthenticatedError("ID token expired.")
		except jwcrypto.jws.InvalidJWSSignature:
			raise asab.exceptions.NotAuthenticatedError("Invalid ID token signature.")
		except ValueError as e:
			raise asab.exceptions.NotAuthenticatedError("Authentication failed: {}".format(e))

		try:
			token_claims = json.loads(token.claims)
		except ValueError:
			raise asab.exceptions.NotAuthenticatedError("Cannot parse ID token claims.")

		return token_claims
