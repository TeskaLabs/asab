import base64
import binascii
import datetime
import functools
import inspect
import json
import logging
import typing
import time

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
		# Globally granted resources
		"*": [
			"authz:superuser",
			"wisdom:access"
		],
		# Resources granted within test-tenant
		"test-tenant": [
			"authz:superuser",
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
				raise ValueError("No 'public_keys_url' provided in [auth] config section.")
			if jwcrypto is None:
				raise ModuleNotFoundError(
					"You are trying to use asab.web.authz without 'jwcrypto' installed. "
					"Please run 'pip install jwcrypto' "
					"or install asab with 'authz' optional dependency.")

		self.AuthServerPublicKey = None  # TODO: Support multiple public keys
		# Limit the frequency of auth server requests to save network traffic
		self.AuthServerCheckCooldown = datetime.timedelta(minutes=5)
		self.AuthServerLastSuccessfulCheck = None


	async def initialize(self, app):
		if self.DevModeEnabled is False:
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
		if self.AuthServerPublicKey is None:
			return False
		return True


	async def get_userinfo_from_id_token(self, bearer_token):
		"""
		Parse the bearer ID token and extract user info.
		"""
		if not self.is_ready():
			# Try to load the public keys again
			if self.AuthServerPublicKey is None:
				await self._fetch_public_keys_if_needed()
			if not self.is_ready():
				L.error("Cannot authenticate request: Failed to load authorization server's public keys.")
				raise aiohttp.web.HTTPUnauthorized()

		try:
			return _get_id_token_claims(bearer_token, self.AuthServerPublicKey)
		except jwcrypto.jws.InvalidJWSSignature:
			# Authz server keys may have changed. Try to reload them.
			L.warning("Invalid ID token signature.")
			await self._fetch_public_keys_if_needed()

		try:
			return _get_id_token_claims(bearer_token, self.AuthServerPublicKey)
		except jwcrypto.jws.InvalidJWSSignature:
			L.error("Cannot authenticate request: Invalid ID token signature.")
			raise asab.exceptions.NotAuthenticatedError()


	def has_superuser_access(self, authorized_resources: typing.Iterable) -> bool:
		"""
		Check if the superuser resource is present in the authorized resource list.
		"""
		return SUPERUSER_RESOURCE in authorized_resources


	def has_resource_access(self, authorized_resources: typing.Iterable, required_resources: typing.Iterable) -> bool:
		"""
		Check if the requested resources or the superuser resource are present in the authorized resource list.
		"""
		if self.has_superuser_access(authorized_resources):
			return True
		for resource in required_resources:
			if resource not in authorized_resources:
				return False
		return True


	async def _fetch_public_keys_if_needed(self, *args, **kwargs):
		"""
		Check if public keys have been fetched from the authorization server and fetch them if not yet.
		"""
		now = datetime.datetime.now(datetime.timezone.utc)
		if self.AuthServerLastSuccessfulCheck is not None \
			and now < self.AuthServerLastSuccessfulCheck + self.AuthServerCheckCooldown:
			# Public keys have been fetched recently
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
		self.AuthServerLastSuccessfulCheck = datetime.datetime.now(datetime.timezone.utc)
		L.log(asab.LOG_NOTICE, "Public key loaded.", struct_data={"url": self.PublicKeysUrl})


	def _authenticate_request(self, handler):
		"""
		Authenticate the request by the JWT ID token in the Authorization header.
		Extract the token claims into request attributes so that they can be used for authorization checks.
		"""
		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]
			if self.DevModeEnabled:
				user_info = self.DevUserInfo
			else:
				# Extract user info from the request Authorization header
				bearer_token = _get_bearer_token(request)
				user_info = await self.get_userinfo_from_id_token(bearer_token)

			assert user_info is not None

			# Add userinfo, tenants and global resources to the request
			request._UserInfo = user_info
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
		for route in aiohttp_app.router.routes():
			# Skip non-coroutines
			if not inspect.iscoroutinefunction(route.handler):
				continue

			# Skip auth for HEAD requests
			if route.method == "HEAD":
				continue

			try:
				self._wrap_handler(route)
			except Exception as e:
				raise Exception("Failed to initialize auth for handler {!r}.".format(route.handler.__qualname__)) from e


	def _wrap_handler(self, route):
		"""
		Inspect handler and apply suitable auth wrappers.
		"""
		# Check if tenant is in route path
		route_info = route.get_info()
		tenant_in_path = "formatter" in route_info and "{tenant}" in route_info["formatter"]

		# Extract the actual handler method for signature checks
		if hasattr(route.handler, "__wrapped__"):
			handler_method = route.handler.__wrapped__
		elif hasattr(route.handler, "__func__"):
			handler_method = route.handler.__func__
		else:
			handler_method = route.handler

		if hasattr(handler_method, "NoAuth"):
			return
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
				handler = self._add_tenant_from_path(handler)
			elif self.MultitenancyEnabled or self.DevModeEnabled:
				handler = self._add_tenant_from_query(handler)
			else:
				handler = self._add_tenant_none(handler)

		handler = self._authenticate_request(handler)
		route._handler = handler


	def _authorize_tenant_request(self, request, tenant):
		"""
		Check access to requested tenant and add tenant resources to the request
		"""
		# Check if tenant access is authorized
		if tenant not in request._Tenants and not request.has_superuser_access():
			L.warning("Tenant not authorized.", struct_data={"tenant": tenant, "sub": request._UserInfo.get("sub")})
			raise asab.exceptions.AccessDeniedError()

		# Extend globally granted resources with tenant-granted resources
		request._Resources = frozenset(request._Resources.union(request._UserInfo["resources"].get(tenant, [])))


	def _add_tenant_from_path(self, handler):
		"""
		Extract tenant from request path and authorize it
		"""

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]
			tenant = request.match_info["tenant"]
			self._authorize_tenant_request(request, tenant)
			return await handler(*args, tenant=tenant, **kwargs)

		return wrapper


	def _add_tenant_from_query(self, handler):
		"""
		Extract tenant from request query and authorize it
		"""

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]
			if "tenant" not in request.query:
				if not self.DevModeEnabled:
					L.error("Request is missing 'tenant' query parameter.")
					raise aiohttp.web.HTTPBadRequest()
				tenant = None
			else:
				tenant = request.query["tenant"]
				self._authorize_tenant_request(request, tenant)
			return await handler(*args, tenant=tenant, **kwargs)

		return wrapper


	def _add_tenant_none(self, handler):
		"""
		Add tenant=None to the handler arguments
		"""

		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			return await handler(*args, tenant=None, **kwargs)

		return wrapper


def _get_id_token_claims(bearer_token: str, auth_server_public_key):
	"""
	Parse and validate JWT ID token and extract the claims (user info)
	"""
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
	except jwcrypto.jwt.JWTExpired:
		L.warning("ID token expired.")
		raise asab.exceptions.NotAuthenticatedError()
	except jwcrypto.jws.InvalidJWSSignature as e:
		raise e
	except ValueError as e:
		L.error(
			"Failed to parse JWT ID token ({}). Please check if the Authorization header contains ID token.".format(e))
		raise aiohttp.web.HTTPBadRequest()
	except Exception:
		L.exception("Failed to parse JWT ID token. Please check if the Authorization header contains ID token.")
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
		L.warning("Cannot parse ID token: Wrong number of '.'.")
		raise aiohttp.web.HTTPBadRequest()

	try:
		claims = json.loads(base64.b64decode(payload.encode("utf-8")))
	except binascii.Error:
		L.warning("Cannot parse ID token: Payload is not base 64.")
		raise aiohttp.web.HTTPBadRequest()
	except json.JSONDecodeError:
		L.warning("Cannot parse ID token: Payload cannot be parsed as JSON.")
		raise aiohttp.web.HTTPBadRequest()

	return claims


def _get_bearer_token(request):
	"""
	Validate the Authorizetion header and extract the Bearer token value
	"""
	authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION)
	if authorization_header is None:
		L.warning("No Authorization header.")
		raise aiohttp.web.HTTPUnauthorized()
	try:
		auth_type, token_value = authorization_header.split(" ", 1)
	except ValueError:
		L.warning("Cannot parse Authorization header.")
		raise aiohttp.web.HTTPBadRequest()
	if auth_type != "Bearer":
		L.warning("Unsupported Authorization header type: {!r}".format(auth_type))
		raise aiohttp.web.HTTPUnauthorized()
	return token_value


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
