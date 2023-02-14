import base64
import binascii
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
		"public_keys_url": "",
		"_disable_token_verifiction": "no",
	}
})


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)
		self._DisableTokenVerification = asab.Config.getboolean("authz", "_disable_token_verifiction")
		self.PublicKeysUrl = asab.Config.get("authz", "public_keys_url")
		if len(self.PublicKeysUrl) == 0 and not self._DisableTokenVerification:
			raise ValueError("No public_keys_url provided in [authz] section.")
		self.PublicKey = None  # TODO: Support multiple public keys
		self.App.PubSub.subscribe("Application.tick/10!", self.initialize)


	async def initialize(self, *args, **kwargs):
		if not self.is_ready():
			await self._get_public_keys()


	def is_ready(self):
		if self._DisableTokenVerification is True:
			return True
		elif self.PublicKey is not None:
			return True
		return False


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
		if not self.is_ready():
			raise Exception("AuthzService is not ready: No public keys loaded yet.")

		if self._DisableTokenVerification:
			return self._get_id_token_claims_without_verification(bearer_token)
		else:
			return self._get_id_token_claims(bearer_token)


	async def _get_public_keys(self):
		async with aiohttp.ClientSession() as session:
			async with session.get(self.PublicKeysUrl) as response:
				if response.status != 200:
					L.error("Error retrieving public keys from authorization server.", struct_data={
						"status": response.status,
						"url": self.PublicKeysUrl,
						"text": await response.text(),
					})
					return
				try:
					data = await response.json()
				except json.JSONDecodeError:
					L.error("Authorization server response cannot be parsed as JSON.", struct_data={
						"url": self.PublicKeysUrl,
						"data": data,
					})
					return
				try:
					key_data = data["keys"].pop()
				except (IndexError, KeyError):
					L.error("Authorization server response contains no public keys.", struct_data={
						"url": self.PublicKeysUrl,
						"data": data,
					})
					return
				try:
					self.PublicKey = jwcrypto.jwk.JWK(**key_data)
				except IndexError:
					L.error("Error reading JSON Web Key.", struct_data={
						"url": self.PublicKeysUrl,
						"data": data,
					})
					return


	def _get_id_token_claims(self, bearer_token: str):
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


	def _get_id_token_claims_without_verification(self, bearer_token: str):
		try:
			header, payload, signature = bearer_token.split(".")
		except IndexError:
			raise asab.exceptions.NotAuthenticatedError("Cannot parse ID token: Wrong number of '.'.")

		try:
			claims = json.loads(base64.b64decode(payload.encode("utf-8")))
		except binascii.Error:
			raise asab.exceptions.NotAuthenticatedError("Cannot parse ID token: Payload is not base 64.")
		except json.JSONDecodeError:
			raise asab.exceptions.NotAuthenticatedError("Cannot parse ID token: Payload cannot be parsed as JSON.")

		return claims
