import base64
import binascii
import json
import logging
import aiohttp
import aiohttp.client_exceptions

import asab
import asab.exceptions

try:
	import jwcrypto.jwk
	import jwcrypto.jwt
	import jwcrypto.jws
except ModuleNotFoundError:
	jwcrypto = None

#

L = logging.getLogger(__name__)

#


asab.Config.add_defaults({
	"authz": {
		"public_keys_url": "",
		"_disable_token_verification": "no",
		"_disable_rbac": "no",
	}
})


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)
		self.RBACDisabled = asab.Config.getboolean("authz", "_disable_rbac")
		self._TokenVerificationDisabled = asab.Config.getboolean("authz", "_disable_token_verification")
		if jwcrypto is None and not self._TokenVerificationDisabled:
			raise ModuleNotFoundError(
				"You are trying to use asab.web.authz without 'jwcrypto' installed. "
				"Please run 'pip install jwcrypto' "
				"or install asab with 'authz' optional dependency.")
		self.PublicKeysUrl = asab.Config.get("authz", "public_keys_url")
		if len(self.PublicKeysUrl) == 0 and not self._TokenVerificationDisabled:
			raise ValueError("No public_keys_url provided in [authz] config section.")
		self.AuthServerPublicKey = None  # TODO: Support multiple public keys
		self.App.PubSub.subscribe("Application.tick/30!", self._fetch_public_keys_if_needed)


	async def initialize(self, app):
		await self._fetch_public_keys_if_needed()


	def is_ready(self):
		if self._TokenVerificationDisabled is True:
			return True
		elif self.AuthServerPublicKey is not None:
			return True
		return False


	async def authorize(self, resources, bearer_token, tenant=None):
		# Use userinfo to make RBAC check
		userinfo = self.userinfo(bearer_token)

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


	def userinfo(self, bearer_token):
		if not self.is_ready():
			L.error("AuthzService is not ready: No public keys loaded yet.")
			return None

		if self._TokenVerificationDisabled:
			return _get_id_token_claims_without_verification(bearer_token)
		else:
			return _get_id_token_claims(bearer_token, self.AuthServerPublicKey)


	async def _fetch_public_keys_if_needed(self, *args, **kwargs):
		if self.is_ready():
			return

		async with aiohttp.ClientSession() as session:
			try:
				async with session.get(self.PublicKeysUrl) as response:
					if response.status != 200:
						L.error("HTTP error while loading public keys.", struct_data={
							"status": response.status,
							"url": self.PublicKeysUrl,
							"text": await response.text(),
						})
						return
					try:
						data = await response.json()
					except json.JSONDecodeError:
						L.error("JSON decoding error while loading public keys.", struct_data={
							"url": self.PublicKeysUrl,
							"data": data,
						})
						return
					try:
						key_data = data["keys"].pop()
					except (IndexError, KeyError):
						L.error("Error while loading public keys: No public keys in server response.", struct_data={
							"url": self.PublicKeysUrl,
							"data": data,
						})
						return
					try:
						public_key = jwcrypto.jwk.JWK(**key_data)
					except Exception as e:
						L.error("JWK decoding error while loading public keys: {}.".format(e), struct_data={
							"url": self.PublicKeysUrl,
							"data": data,
						})
						return
			except aiohttp.client_exceptions.ClientConnectorError as e:
				L.error("Connection error while loading public keys: {}".format(e), struct_data={
					"url": self.PublicKeysUrl,
				})
				return

		self.AuthServerPublicKey = public_key
		L.log(asab.LOG_NOTICE, "Public key loaded.", struct_data={"url": self.PublicKeysUrl})


def _get_id_token_claims(bearer_token: str, auth_server_public_key):
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
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


def _get_id_token_claims_without_verification(bearer_token: str):
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
