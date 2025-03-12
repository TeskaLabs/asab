import typing
import time
import os
import json
import aiohttp.web
import logging

from .abc import AuthProviderABC
from ..authorization import Authorization


L = logging.getLogger(__name__)


_MOCK_AUTH_CLAIMS_DEFAULT = {
	# Token issuer
	"iss": "auth.test.loc",
	# Token issued at (timestamp)
	"iat": int(time.time()),
	# Token expires at (timestamp)
	"exp": int(time.time()) + 5 * 365 * 24 * 3600,
	# Authorized party
	"azp": "my-asab-app",
	# Audience
	"aud": "my-asab-app",
	# Subject (Unique user ID)
	"sub": "abc:xyz:799b53e0",
	# Subject's preferred username
	"preferred_username": "little-capybara",
	# Subject's email
	"email": "capybara1999@example.com",
	# Authorized tenants and resources
	"resources": {
		# Globally authorized resources
		"*": [
			"authz:superuser",
		],
		# Resources authorized within the tenant "default"
		"default": [
			"authz:superuser",
			"some-test-data:access",
		],
	},
	# List of tenants that the user is a member of.
	# These tenants are NOT AUTHORIZED!
	"tenants": ["default", "test-tenant", "another-tenant"]
}


class MockAuthProvider(AuthProviderABC):
	"""
	Authenticates and authorizes requests with preconfigured authorization claims.

	Development only, not optimized for production use.
	"""
	Type = "mock"

	def __init__(self, app, auth_claims_path: typing.Optional[str] = None):
		super().__init__(app)
		self.Authorization: typing.Optional[Authorization] = None
		self._prepare_authorization(auth_claims_path)


	async def initialize(self):
		pass


	async def authorize(self, request: aiohttp.web.Request) -> Authorization:
		return self.Authorization


	def _prepare_authorization(self, auth_claims_path: typing.Optional[str] = None):
		"""
		Prepare the authorization object from specified file or fallback to default claims.

		Args:
			auth_claims_path: Path to the file with custom auth claims.
		"""
		# Load custom auth claims from a file
		if auth_claims_path and os.path.isfile(auth_claims_path):
			with open(auth_claims_path, "rb") as f:
				auth_claims = json.load(f)
		elif os.path.isfile("/conf/mock-claims.json"):
			with open(auth_claims_path, "rb") as f:
				auth_claims = json.load(f)
		elif os.path.isfile("/conf/mock-userinfo.json"):
			with open(auth_claims_path, "rb") as f:
				auth_claims = json.load(f)
		else:
			auth_claims = _MOCK_AUTH_CLAIMS_DEFAULT

		# Validate auth claims
		resources = auth_claims.get("resources", {})
		if not isinstance(resources, dict) or not all(
			map(lambda kv: isinstance(kv[0], str) and isinstance(kv[1], list), resources.items())
		):
			raise ValueError("The 'resources' claim must be an object with string keys and array values.")

		L.warning(
			"Mock authorization provider is enabled. All web requests will be provided with {!r} which also"
			"grants access to the following tenants: {}. To customize the authorization (add or "
			"remove tenants and resources, change username etc.), provide your own user info in {!r}.".format(
				self.Authorization,
				list(t for t in auth_claims.get("resources", {}).keys() if t != "*"),
				auth_claims_path
			)
		)
		self.Authorization = Authorization(auth_claims)
