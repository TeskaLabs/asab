import base64
import binascii
import datetime
import functools
import inspect
import json
import logging
import os.path
import time
import enum
import typing

import aiohttp
import aiohttp.web
import aiohttp.client_exceptions

from ...abc.service import Service
from ...config import Config
from ...exceptions import NotAuthenticatedError, AccessDeniedError
from ...api.discovery import NotDiscoveredError
from ...library.service import LogObsolete
from ...utils import string_to_boolean
from ...contextvars import Tenant, Authz
from .authz import Authorization

try:
	import jwcrypto.jwk
	import jwcrypto.jwt
	import jwcrypto.jws
except ModuleNotFoundError:
	jwcrypto = None

#

L = logging.getLogger(__name__)

#

# Used for mock authorization
MOCK_USERINFO_DEFAULT = {
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

SUPERUSER_RESOURCE = "authz:superuser"


class AuthMode(enum.Enum):
	ENABLED = enum.auto()
	DISABLED = enum.auto()
	MOCK = enum.auto()


class AuthService(Service):
	"""
	Provides authentication and authorization of incoming requests.

	Configuration:
		Configuration section: auth
		Configuration options:
			public_keys_url:
				- default: ""
				- URL containing the authorization server's public JWKey set (usually found at "/.well-known/jwks.json")
			enabled:
				- default: "yes"
				- options: "yes", "no", "mocked"
				- Switch authentication and authorization on, off or activate mock mode.
				- In MOCK MODE
					- no authorization server is needed,
					- all incoming requests are mock-authorized with pre-defined user info,
					- custom mock user info can supplied in a JSON file.
			mock_user_info_path:
				- default: "/conf/mock-userinfo.json"
	"""

	_PUBLIC_KEYS_URL_DEFAULT = "http://localhost:3081/.well-known/jwks.json"


	def __init__(self, app, service_name="asab.AuthService"):
		super().__init__(app, service_name)
		self.PublicKeysUrl = Config.get("auth", "public_keys_url") or None

		# To enable Service Discovery, initialize Api Service and call its initialize_zookeeper() method before AuthService initialization
		self.DiscoveryService = self.App.get_service("asab.DiscoveryService")

		enabled = Config.get("auth", "enabled", fallback=True)
		if enabled == "mock":
			self.Mode = AuthMode.MOCK
		elif string_to_boolean(enabled):
			self.Mode = AuthMode.ENABLED
		else:
			self.Mode = AuthMode.DISABLED

		if self.Mode == AuthMode.DISABLED:
			pass
		elif self.Mode == AuthMode.MOCK:
			self.MockUserInfo = self._prepare_mock_user_info()
		elif jwcrypto is None:
			raise ModuleNotFoundError(
				"You are trying to use asab.web.auth module without 'jwcrypto' installed. "
				"Please run 'pip install jwcrypto' "
				"or install asab with 'authz' optional dependency.")
		elif not self.PublicKeysUrl and self.DiscoveryService is None:
			self.PublicKeysUrl = self._PUBLIC_KEYS_URL_DEFAULT
			L.warning(
				"No 'public_keys_url' provided in [auth] config section. "
				"Defaulting to {!r}.".format(self._PUBLIC_KEYS_URL_DEFAULT)
			)

		self.TrustedPublicKeys: jwcrypto.jwk.JWKSet = jwcrypto.jwk.JWKSet()
		# Limit the frequency of auth server requests to save network traffic
		self.AuthServerCheckCooldown = datetime.timedelta(minutes=5)
		self.AuthServerLastSuccessfulCheck = None

		if self.Mode == AuthMode.ENABLED:
			self.App.TaskService.schedule(self._fetch_public_keys_if_needed())

		self.Authorizations: typing.Dict[typing.Tuple[str, str], Authorization] = {}
		self.App.PubSub.subscribe("Application.housekeeping!", self.delete_invalid_authorizations)

		# Try to auto-install authorization middleware
		self.install()


	def _prepare_mock_user_info(self):
		# Load custom user info
		mock_user_info_path = Config.get("auth", "mock_user_info_path")
		if os.path.isfile(mock_user_info_path):
			with open(mock_user_info_path, "rb") as fp:
				user_info = json.load(fp)
		else:
			user_info = MOCK_USERINFO_DEFAULT
		# Validate user info
		resources = user_info.get("resources", {})
		if not isinstance(resources, dict) or not all(
			map(lambda kv: isinstance(kv[0], str) and isinstance(kv[1], list), resources.items())
		):
			raise ValueError("User info 'resources' must be an object with string keys and array values.")
		L.warning(
			"AuthService is running in MOCK MODE. All web requests will be authorized with mock user info, which "
			"currently grants access to the following tenants: {}. To customize mock mode authorization (add or "
			"remove tenants and resources, change username etc.), provide your own user info in {!r}.".format(
				list(t for t in user_info.get("resources", {}).keys() if t != "*"),
				mock_user_info_path))
		return user_info


	def is_enabled(self) -> bool:
		"""
		Check if the AuthService is enabled. Mock mode counts as enabled too.
		"""
		return self.Mode in {AuthMode.ENABLED, AuthMode.MOCK}


	def install(self, web_container=None):
		"""
		Apply authorization to all web handlers in a web container, according to their arguments and path parameters.

		:param web_container: Web container to be protected by authorization.
		:type web_container: asab.web.WebContainer
		"""
		if web_container is None:
			# Locate web container if there is only one
			web_service = self.App.get_service("asab.WebService")
			if len(web_service.Containers) != 1:
				return
			web_container = web_service.WebContainer

		# Check that the middleware has not been installed yet
		for middleware in web_container.WebApp.on_startup:
			if middleware == self._wrap_handlers:
				return

		web_container.WebApp.on_startup.append(self._wrap_handlers)


	def is_ready(self):
		"""
		Check if the service is ready to authorize requests.
		"""
		if self.Mode == AuthMode.DISABLED:
			return True
		if self.Mode == AuthMode.MOCK:
			return True
		if not self.TrustedPublicKeys["keys"]:
			return False
		return True


	async def build_authorization(self, id_token: str) -> Authorization:
		"""
		Build authorization from ID token string.

		:param id_token: Base64-encoded JWToken from Authorization header
		:return: Valid asab.web.auth.Authorization object
		"""
		if not self.is_enabled():
			raise ValueError("Cannot build Authorization when AuthService is disabled.")

		# Try if the object already exists
		authz = self.Authorizations.get(id_token)
		if authz is not None:
			try:
				authz.require_valid()
			except AccessDeniedError as e:
				del self.Authorizations[id_token]
				raise e
			return authz

		# Create a new Authorization object and store it
		if self.Mode == AuthMode.MOCK:
			assert id_token == "MOCK"
			authz = Authorization(self, self.MockUserInfo)
		else:
			userinfo = await self._get_userinfo_from_id_token(id_token)
			authz = Authorization(self, userinfo)

		self.Authorizations[id_token] = authz
		return authz


	async def delete_invalid_authorizations(self):
		"""
		Check for expired Authorization objects and delete them
		"""
		# Find expired
		expired = []
		for key, authz in self.Authorizations.items():
			if not authz.is_valid():
				expired.append(key)

		# Delete expired
		for key in expired:
			del self.Authorizations[key]


	def bearer_token_from_request(self, request):
		"""
		Validate the Authorizetion header and extract the Bearer token value
		"""
		if self.Mode == AuthMode.MOCK:
			return "MOCK"

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


	async def _fetch_public_keys_if_needed(self, *args, **kwargs):
		"""
		Check if public keys have been fetched from the authorization server and fetch them if not yet.
		"""
		# TODO: Refactor into Key Providers
		# Add internal shared auth key
		if self.DiscoveryService is not None:
			if self.DiscoveryService.InternalAuthKey is not None:
				self.TrustedPublicKeys.add(self.DiscoveryService.InternalAuthKey.public())
			else:
				L.debug("Internal auth key is not ready yet.")
				self.App.TaskService.schedule(self._fetch_public_keys_if_needed())

			if not self.PublicKeysUrl:
				# Only internal authorization is supported
				return

		# Either DiscoveryService or PublicKeysUrl must be defined
		assert self.PublicKeysUrl is not None

		now = datetime.datetime.now(datetime.timezone.utc)
		if self.AuthServerLastSuccessfulCheck is not None \
			and now < self.AuthServerLastSuccessfulCheck + self.AuthServerCheckCooldown:
			# Public keys have been fetched recently
			return


		async def fetch_keys(session):
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
			return public_key

		if self.DiscoveryService is None:
			async with aiohttp.ClientSession() as session:
				public_key = await fetch_keys(session)

		else:
			async with self.DiscoveryService.session() as session:
				try:
					public_key = await fetch_keys(session)
				except NotDiscoveredError as e:
					L.error("Service Discovery error while loading public keys: {}".format(e), struct_data={
						"url": self.PublicKeysUrl,
					})
					return

		if public_key is None:
			return

		self.TrustedPublicKeys.add(public_key)
		self.AuthServerLastSuccessfulCheck = datetime.datetime.now(datetime.timezone.utc)
		L.debug("Public key loaded.", struct_data={"url": self.PublicKeysUrl})


	def _authorize_request(self, handler):
		"""
		Authenticate the request by the JWT ID token in the Authorization header.
		Extract the token claims into Authorization context so that they can be used for authorization checks.
		"""
		@functools.wraps(handler)
		async def wrapper(*args, **kwargs):
			request = args[-1]

			if not self.is_enabled():
				return await handler(*args, **kwargs)

			bearer_token = self.bearer_token_from_request(request)
			authz = await self.build_authorization(bearer_token)

			# Authorize tenant context
			tenant = Tenant.get(None)
			if tenant is not None:
				authz.require_tenant_access()

			authz_ctx = Authz.set(authz)
			try:
				return await handler(*args, **kwargs)
			finally:
				Authz.reset(authz_ctx)

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
		handler_method = route.handler
		while hasattr(handler_method, "__wrapped__"):
			# While loop unwraps handlers wrapped in multiple decorators.
			# NOTE: This requires all the decorators to use @functools.wraps().
			handler_method = handler_method.__wrapped__

		if hasattr(handler_method, "__func__"):
			handler_method = handler_method.__func__

		if hasattr(handler_method, "NoAuth"):
			return
		argspec = inspect.getfullargspec(handler_method)
		args = set(argspec.kwonlyargs).union(argspec.args)

		# Extract the whole handler for wrapping
		handler = route.handler

		# Apply the decorators IN REVERSE ORDER (the last applied wrapper affects the request first)

		# 3) Pass authorization attributes to handler method
		if "resources" in args:
			LogObsolete.warning(
				"The 'resources' argument is deprecated. "
				"Use the access-checking methods of asab.contextvars.Authz instead.",
				struct_data={"handler": handler.__qualname__, "eol": "2025-03-01"},
			)
			handler = _pass_resources(handler)
		if "user_info" in args:
			LogObsolete.warning(
				"The 'user_info' argument is deprecated. "
				"Use the Authorization object in asab.contextvars.Authz instead.",
				struct_data={"handler": handler.__qualname__, "eol": "2025-03-01"},
			)
			handler = _pass_user_info(handler)
		if "tenant" in args:
			handler = _pass_tenant(handler)
		if "authz" in args:
			handler = _pass_authz(handler)

		# 2) Authenticate and authorize request, authorize tenant from context, set Authorization context
		handler = self._authorize_request(handler)

		# 1.5) Set tenant context from obsolete locations (no authorization yet)
		# TODO: Deprecated. Ignore tenant in path and query, always use request headers instead.
		if tenant_in_path:
			handler = _set_tenant_context_from_url_path(handler)
		else:
			handler = _set_tenant_context_from_url_query(handler)

		# 1) Set tenant context (no authorization yet)
		# TODO: This should be eventually done by TenantService
		handler = _set_tenant_context_from_request_header(handler)

		route._handler = handler


	async def _get_userinfo_from_id_token(self, bearer_token):
		"""
		Parse the bearer ID token and extract user info.
		"""
		if not self.is_ready():
			# Try to load the public keys again
			if not self.TrustedPublicKeys["keys"]:
				await self._fetch_public_keys_if_needed()
			if not self.is_ready():
				L.error("Cannot authenticate request: Failed to load authorization server's public keys.")
				raise aiohttp.web.HTTPUnauthorized()

		try:
			return _get_id_token_claims(bearer_token, self.TrustedPublicKeys)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey):
			# Authz server keys may have changed. Try to reload them.
			await self._fetch_public_keys_if_needed()

		try:
			return _get_id_token_claims(bearer_token, self.TrustedPublicKeys)
		except (jwcrypto.jws.InvalidJWSSignature, jwcrypto.jwt.JWTMissingKey) as e:
			L.error("Cannot authenticate request: {}".format(str(e)))
			raise NotAuthenticatedError()


def _get_id_token_claims(bearer_token: str, auth_server_public_key):
	"""
	Parse and validate JWT ID token and extract the claims (user info)
	"""
	assert jwcrypto is not None
	try:
		token = jwcrypto.jwt.JWT(jwt=bearer_token, key=auth_server_public_key)
	except jwcrypto.jwt.JWTExpired:
		L.warning("ID token expired.")
		raise NotAuthenticatedError()
	except jwcrypto.jwt.JWTMissingKey as e:
		raise e
	except jwcrypto.jws.InvalidJWSSignature as e:
		raise e
	except ValueError as e:
		L.error(
			"Failed to parse JWT ID token ({}). Please check if the Authorization header contains ID token.".format(e))
		raise aiohttp.web.HTTPBadRequest()
	except jwcrypto.jws.InvalidJWSObject as e:
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


def _pass_user_info(handler):
	"""
	Add user info to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		authz = Authz.get(None)
		return await handler(*args, user_info=authz.UserInfo if authz is not None else None, **kwargs)
	return wrapper


def _pass_resources(handler):
	"""
	Add resources to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		authz = Authz.get(None)
		return await handler(*args, resources=authz.authorized_resources() if authz is not None else None, **kwargs)
	return wrapper


def _pass_tenant(handler):
	"""
	Add tenant to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		return await handler(*args, tenant=Tenant.get(None), **kwargs)
	return wrapper


def _pass_authz(handler):
	"""
	Add Auhorization object to the handler arguments
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		authz = Authz.get(None)
		return await handler(*args, authz=authz, **kwargs)
	return wrapper


def _set_tenant_context_from_request_header(handler):
	"""
	Extract tenant from request header (X-Tenant or Sec-Websocket-Protocol) and add it to context
	"""
	def get_tenant_from_header(request) -> str:
		if request.headers.get("Upgrade") == "websocket":
			# Get tenant from Sec-Websocket-Protocol header for websocket requests
			protocols = request.headers.get("Sec-Websocket-Protocol", "")
			for protocol in protocols.split(", "):
				protocol = protocol.strip()
				if protocol.startswith("tenant_"):
					return protocol[7:]
			else:
				return None
		else:
			# Get tenant from X-Tenant header for HTTP requests
			return request.headers.get("X-Tenant")

	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		tenant = get_tenant_from_header(request)

		if tenant is None:
			response = await handler(*args, **kwargs)
		else:
			assert len(tenant) < 128  # Limit tenant name length to 128 characters to maintain sanity
			tenant_ctx = Tenant.set(tenant)
			try:
				response = await handler(*args, **kwargs)
			finally:
				Tenant.reset(tenant_ctx)

		return response

	return wrapper


def _set_tenant_context_from_url_query(handler):
	"""
	Extract tenant from request query and add it to context
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		header_tenant = Tenant.get(None)
		tenant = request.query.get("tenant")

		if tenant is None:
			# No tenant in query
			response = await handler(*args, **kwargs)
		elif header_tenant is not None:
			# Tenant from header must not be overwritten by a different tenant in query!
			if tenant != header_tenant:
				L.error("Tenant from URL query does not match tenant from header.", struct_data={
					"header_tenant": header_tenant, "query_tenant": tenant})
				raise AccessDeniedError()
			# Tenant in query matches tenant in header
			response = await handler(*args, **kwargs)
		else:
			# No tenant in header, only in query
			assert len(tenant) < 128  # Limit tenant name length to 128 characters to maintain sanity
			tenant_ctx = Tenant.set(tenant)
			try:
				response = await handler(*args, **kwargs)
			finally:
				Tenant.reset(tenant_ctx)

		return response

	return wrapper


def _set_tenant_context_from_url_path(handler):
	"""
	Extract tenant from request URL path and add it to context
	"""
	@functools.wraps(handler)
	async def wrapper(*args, **kwargs):
		request = args[-1]
		header_tenant = Tenant.get(None)
		tenant = request.match_info.get("tenant")

		if header_tenant is not None:
			# Tenant from header must not be overwritten by a different tenant in path!
			if tenant != header_tenant:
				L.error("Tenant from URL path does not match tenant from header.", struct_data={
					"header_tenant": header_tenant, "path_tenant": tenant})
				raise AccessDeniedError()
			# Tenant in path matches tenant in header
			response = await handler(*args, **kwargs)
		else:
			# No tenant in header, only in path
			assert len(tenant) < 128  # Limit tenant name length to 128 characters to maintain sanity
			tenant_ctx = Tenant.set(tenant)
			try:
				response = await handler(*args, **kwargs)
			finally:
				Tenant.reset(tenant_ctx)

		return response

	return wrapper
