import base64
import binascii
import functools
import inspect
import json
import logging
import typing

import aiohttp
import aiohttp.web
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

# Mock user info used in dev mode
DEV_USERINFO_DEFAULT = {
	"iss": "auth.test.loc",      # Token issuer
	"iat": 1682077901,         # Token issued at (timestamp)
	"exp": 1682092289,         # Token expires at (timestamp)
	"azp": "my-asab-app",        # Authorized party
	"aud": "my-asab-app",        # Audience
	"sub": "abc:xyz:799b53e0",   # Subject (Unique user ID)
	"preferred_username": "little-capybara",  # Subject's preferred username
	"email": "capybara1999@example.com",      # Subject's email
	# Authorized tenants and resources
	"resources": {
		# Globally granted resources
		"*": [
			"wisdom:access"
		],
		# Resources granted within test-tenant
		"test-tenant": [
			"wisdom:access",
			"cake:admire",
			"cake:smell",
			"cake:eat",
		],
	},
	# Subject's assigned (not authorized!) tenants
	"tenants": [
		"test-tenant",
		"another-tenant",
	]
}

SUPERUSER_RESOURCE = "authz:superuser"

asab.Config.add_defaults({
	"auth": {
		# URL location containing the authorization server's public JWK keys
		"public_keys_url": "",

		# Whether the app is tenant-aware
		"multitenancy": "yes",

		# In DEV MODE
		# - no authorization server is needed,
		# - all incoming requests are "authorized" with custom mocked user info data loaded from a JSON file,
		"dev_mode": "no",
		"dev_user_info_path": "",
	}
})


class AuthService(asab.Service):
	"""
	Provides authentication and authorization of incoming requests
	"""

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)
		self.MultitenancyEnabled = asab.Config.getboolean("auth", "multitenancy")
		self.PublicKeysUrl = asab.Config.get("auth", "public_keys_url")

		self.DevModeEnabled = asab.Config.getboolean("auth", "dev_mode")
		if self.DevModeEnabled:
			L.warning("AuthService is running in developer mode.")
			dev_user_info = asab.Config.get("auth", "dev_user_info_path")
			if dev_user_info:
				with open(dev_user_info, "rb") as fp:
					self.DevUserInfo = json.load(fp)
			else:
				self.DevUserInfo = DEV_USERINFO_DEFAULT
		else:
			if len(self.PublicKeysUrl) == 0:
				raise ValueError("No public_keys_url provided in [auth] config section.")
			if jwcrypto is None:
				raise ModuleNotFoundError(
					"You are trying to use asab.web.authz without 'jwcrypto' installed. "
					"Please run 'pip install jwcrypto' "
					"or install asab with 'authz' optional dependency.")

		self.AuthServerPublicKey = None  # TODO: Support multiple public keys

		# TODO: Fetch public keys if validation fails (instead of periodic fetch)
		self.App.PubSub.subscribe("Application.tick/30!", self._fetch_public_keys_if_needed)


	async def initialize(self, app):
		await self._fetch_public_keys_if_needed()


	def install(self, web_container):
		"""
		Apply authorization to web handlers depending on their arguments and path parameters
		"""
		# TODO: Call this automatically if there is only one container
		web_container.WebApp.on_startup.append(self._wrap_handlers)


	def is_ready(self):
		"""
		Check if the service is ready to authorize requests.
		"""
		if self.DevModeEnabled is True:
			return True
		elif self.AuthServerPublicKey is not None:
			return True
		return False


	def userinfo(self, bearer_token):
		"""
		Parse the bearer ID token and extract user info.
		"""
		if not self.is_ready():
			L.error("AuthzService is not ready: No public keys loaded yet.")
			return None

		if self.DevModeEnabled:
			return self.DevUserInfo
		else:
			return _get_id_token_claims(bearer_token, self.AuthServerPublicKey)


	@staticmethod
	def has_superuser_access(self, authorized_resources: typing.Iterable) -> bool:
		"""
		Check if the superuser resource is present in the authorized resource list.
		"""
		return SUPERUSER_RESOURCE in authorized_resources


	@staticmethod
	def has_resource_access(self, authorized_resources: typing.Iterable, required_resources: typing.Iterable) -> bool:
		"""
		Check if the requested resources or the superuser resource are present in the authorized resource list.
		"""
		if self.has_superuser_access(authorized_resources):
			return True
		for resource in required_resources:
			if resource not in authorized_resources:
				return False


	async def _fetch_public_keys_if_needed(self, *args, **kwargs):
		"""
		Check if public keys have been fetched from the authorization server and fetch them if not yet.
		"""
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


	def _authenticate_request(self, handler):
		"""
		Authenticate the request by the JWT ID token in the Authorization header.
		Extract the token claims into request attributes so that they can be used for authorization checks.
		"""
		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			if not self.is_ready():
				L.error("Cannot authenticate request: AuthzService is not ready.")
				raise aiohttp.web.HTTPUnauthorized()

			request = args[-1]
			bearer_token = _get_bearer_token(request)

			# Add userinfo, tenants and global resources to the request
			request._UserInfo = self.userinfo(bearer_token)

			resource_dict = request._UserInfo["resources"]
			request._Resources = frozenset(resource_dict.get("*", []))
			request._Tenants = frozenset(t for t in resource_dict.keys() if t != "*")

			# Add access control methods to the request
			def has_resource_access(*required_resources: list) -> bool:
				return self.has_resource_access(request._Resources, required_resources)
			request.has_resource_access = has_resource_access

			def has_superuser_access() -> bool:
				return self.has_superuser_access(request._Resources)
			request.has_superuser_access = has_superuser_access

			return await handler(*args, **kwargs)
		return wrapper


	async def _wrap_handlers(self, aiohttp_app):
		"""
		Inspect all registered handlers and wrap them in decorators according to their parameters.
		"""
		# Iterate through registered routes
		for route in aiohttp_app.router.routes():
			if not inspect.iscoroutinefunction(route.handler):
				continue

			# Check if tenant is in route path
			route_info = route.get_info()
			tenant_in_path = "formatter" in route_info and "{tenant}" in route_info["formatter"]

			# Extract the actual handler method for signature checks
			if hasattr(route.handler, "__wrapped__"):
				handler_method = route.handler.__wrapped__
			else:
				handler_method = route.handler.__func__

			if hasattr(handler_method, "NoAuth"):
				continue

			argspec = inspect.getfullargspec(handler_method)
			args = set(argspec.kwonlyargs).union(argspec.args)

			# Extract the whole handler for wrapping
			handler = route.handler

			# Apply the decorators in reverse order (the last applied wrapper affects the request first)
			if "resources" in args:
				handler = _add_resources(handler)
			if "user_info" in args:
				handler = _add_user_info(handler)
			if "tenant" in args:
				if tenant_in_path:
					handler = _add_tenant_from_path(handler)
				elif self.MultitenancyEnabled:
					handler = _add_tenant_from_query(handler)
				else:
					handler = _add_tenant_none(handler)

			handler = self._authenticate_request(handler)
			route._handler = handler


def _get_id_token_claims(bearer_token: str, auth_server_public_key):
	"""
	Parse and validate JWT ID token and extract the claims (user info)
	"""
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
	except jwcrypto.jwt.JWTExpired:
		raise asab.exceptions.NotAuthenticatedError("ID token expired.")
	except jwcrypto.jws.InvalidJWSSignature:
		raise asab.exceptions.NotAuthenticatedError("Invalid ID token signature.")
	except Exception:
		L.exception("Failed to parse JWT ID token.")
		raise aiohttp.web.HTTPBadRequest()

	try:
		token_claims = json.loads(token.claims)
	except Exception:
		L.exception("Failed to parse JWT token claims.")
		raise aiohttp.web.HTTPBadRequest()

	return token_claims


def _get_id_token_claims_without_verification(bearer_token: str):
	"""
	Parse JWT ID token without validation and extract the claims (user info)
	"""
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


def _get_bearer_token(request):
	"""
	Validate the Authorizetion header and extract the Bearer token value
	"""
	authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
	if authorization_header is None:
		L.warning("No Authorization header")
		raise aiohttp.web.HTTPUnauthorized()
	try:
		auth_type, token_value = authorization_header.split(" ", 1)
	except ValueError:
		L.warning("Invalid Authorization header")
		raise aiohttp.web.HTTPUnauthorized()
	if auth_type != "Bearer":
		L.warning("Unsupported Authorization header type: {!r}".format(auth_type))
		raise aiohttp.web.HTTPUnauthorized()
	return token_value


def _authorize_tenant_request(request, tenant):
	"""
	Check access to requested tenant and add tenant resources to the request
	"""
	if tenant not in request._Tenants:
		L.warning("Tenant not authorized", struct_data={"tenant": tenant, "sub": request._UserInfo.get("sub")})
		raise aiohttp.web.HTTPUnauthorized()
	request._Resources = request._UserInfo["resources"][tenant]


def _add_tenant_from_path(handler):
	"""
	Extract tenant from request path and authorize it
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		tenant = request.match_info["tenant"]
		_authorize_tenant_request(request, tenant)
		return await handler(*args, tenant=tenant, **kwargs)
	return wrapper


def _add_tenant_from_query(handler):
	"""
	Extract tenant from request query and authorize it
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		if "tenant" not in request.query:
			L.error("Request is missing 'tenant' query parameter.")
			raise aiohttp.web.HTTPBadRequest()
		tenant = request.query["tenant"]
		_authorize_tenant_request(request, tenant)
		return await handler(*args, tenant=tenant, **kwargs)
	return wrapper


def _add_tenant_none(handler):
	"""
	Add tenant=None to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		return await handler(*args, tenant=None, **kwargs)
	return wrapper


def _add_user_info(handler):
	"""
	Add user info to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		return await handler(*args, user_info=request._UserInfo, **kwargs)
	return wrapper


def _add_resources(handler):
	"""
	Add resources to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		return await handler(*args, resources=request._Resources, **kwargs)
	return wrapper
