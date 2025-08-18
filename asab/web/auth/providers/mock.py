import typing
import time
import os
import json
import aiohttp.web
import logging

from .... import utils
from .abc import AuthProviderABC
from ..authorization import Authorization


L = logging.getLogger(__name__)


_MOCK_AUTH_CLAIMS_DEFAULT = {
	# Token issuer
	"iss": "my-app.asab",
	# Token issued at (timestamp)
	"iat": "now - 10s",
	# Token expires at (timestamp)
	"exp": "now + 1y",
	# Audience
	"aud": "my-app.asab",
	# Subject (Unique user ID)
	"sub": "asab:user:capybara1999",
	# Subject's preferred username
	"preferred_username": "littlecapybara",
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
		auth_claims = _MOCK_AUTH_CLAIMS_DEFAULT.copy()

		# Load custom auth claims from a file
		for path in [auth_claims_path, "/conf/mock-claims.json", "/conf/mock-userinfo.json"]:
			if path is not None and os.path.isfile(path):
				with open(path, "rb") as f:
					for k, v in json.load(f).items():
						if v is None:
							del auth_claims[k]
						else:
							auth_claims[k] = v
				break

		# Convert duration values to timestamps
		for k in ("iat", "exp"):
			v = auth_claims[k]
			if isinstance(v, str):
				v = v.replace(" ", "")
				if v.startswith("now+"):
					auth_claims[k] = int(time.time()) + utils.convert_to_seconds(v[4:])
				if v.startswith("now-"):
					auth_claims[k] = int(time.time()) - utils.convert_to_seconds(v[4:])

		# Validate auth claims
		resources = auth_claims.get("resources", {})
		if not isinstance(resources, dict) or not all(
			map(lambda kv: isinstance(kv[0], str) and isinstance(kv[1], list), resources.items())
		):
			raise ValueError("The 'resources' claim must be an object with string keys and array values.")

		self.Authorization = Authorization(auth_claims)
		L.warning(
			"Mock authorization provider is enabled. All web requests will be provided with {!r} which also "
			"grants access to the following tenants: {}. To customize the authorization (add or "
			"remove tenants and resources, change username etc.), provide your own claims in {!r}.".format(
				self.Authorization,
				list(t for t in auth_claims.get("resources", {}).keys() if t != "*"),
				auth_claims_path
			)
		)
