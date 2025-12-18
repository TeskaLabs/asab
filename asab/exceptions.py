import aiohttp.web
import aiohttp.hdrs
import typing


class _WWWAuthenticateMixin:
	def update_www_authenticate(
		self,
		*,
		realm: typing.Optional[str] = None,
		scope: typing.Optional[typing.List[str]] = None,
		error: typing.Optional[str] = None,
		error_description: typing.Optional[str] = None,
		error_uri: typing.Optional[str] = None,
		resource_metadata: typing.Optional[str] = None,
	):
		if not hasattr(self, "WWWAuthenticate"):
			self.WWWAuthenticate = {}
		if realm is not None:
			self.WWWAuthenticate["realm"] = realm
		if scope is not None:
			self.WWWAuthenticate["scope"] = scope
		if error is not None:
			self.WWWAuthenticate["error"] = error
		if error_description is not None:
			self.WWWAuthenticate["error_description"] = error_description
		if error_uri is not None:
			self.WWWAuthenticate["error_uri"] = error_uri
		if resource_metadata is not None:
			self.WWWAuthenticate["resource_metadata"] = resource_metadata

		# Update the header
		if hasattr(self, "headers"):
			self.headers[aiohttp.hdrs.WWW_AUTHENTICATE] = "Bearer " + ", ".join(
				"{}=\"{}\"".format(k, (" ".join(v) if k == "scope" else v))
				for k, v in self.WWWAuthenticate.items()
				if v is not None
			)


class ValidationError(Exception):
	"""
	Request cannot be processed because it does not match expected schema
	"""
	# TODO: Inherit from aiohttp.web.HTTPBadRequest
	pass


class NotAuthenticatedError(_WWWAuthenticateMixin, aiohttp.web.HTTPUnauthorized):
	"""
	Request could not be authenticated
	"""
	def __init__(
		self,
		*args,
		realm: typing.Optional[str] = "asab",
		scope: typing.Optional[typing.List[str]] = None,
		error: typing.Optional[str] = "invalid_token",
		error_description: typing.Optional[str] = None,
		error_uri: typing.Optional[str] = None,
		resource_metadata: typing.Optional[str] = None,
		**kwargs
	):
		"""
		Args:
			*args:
			realm: Defines the protection space within the server being accessed (RFC2617)
			scope: The scope required to access the resource (RFC6750)
			error: ASCII error code (RFC6750)
			error_description: Human-readable UTF-8 encoded text providing additional error information (RFC6750)
			resource_metadata: The URL of the protected resource metadata (RFC9728)
			**kwargs:
		"""
		super().__init__(*args, **kwargs)
		self.WWWAuthenticate = {}
		self.update_www_authenticate(
			realm=realm,
			scope=scope,
			error=error,
			error_description=error_description,
			error_uri=error_uri,
			resource_metadata=resource_metadata
		)


class AccessDeniedError(_WWWAuthenticateMixin, aiohttp.web.HTTPForbidden):
	"""
	Authenticated subject does not have the rights to access requested resource
	"""
	def __init__(
		self,
		*args,
		realm: typing.Optional[str] = "asab",
		scope: typing.Optional[typing.List[str]] = None,
		error: typing.Optional[str] = "insufficient_scope",
		error_description: typing.Optional[str] = None,
		error_uri: typing.Optional[str] = None,
		resource_metadata: typing.Optional[str] = None,
		**kwargs
	):
		"""
		Args:
			*args:
			realm: Defines the protection space within the server being accessed (RFC2617)
			scope: The scope required to access the resource (RFC6750)
			error: ASCII error code (RFC6750)
			error_description: Human-readable UTF-8 encoded text providing additional error information (RFC6750)
			resource_metadata: The URL of the protected resource metadata (RFC9728)
			**kwargs:
		"""
		super().__init__(*args, **kwargs)
		self.WWWAuthenticate = {}
		self.update_www_authenticate(
			realm=realm,
			scope=scope,
			error=error,
			error_description=error_description,
			error_uri=error_uri,
			resource_metadata=resource_metadata
		)


class Conflict(Exception):
	"""
	Request cannot be satisfied because it would introduce a state that violates some uniqueness requirement
	"""
	# TODO: Inherit from aiohttp.web.HTTPConflict
	# TODO: Handle when the value of `key` or `value` is actually `None`
	def __init__(self, message=None, *args, key=None, value=None):
		self.Key = key
		self.Value = value

		if message is None:
			if key is not None:
				if value is not None:
					message = "Conflict in field {}: {}".format(repr(key), repr(value))
				else:
					message = "Conflict in field {}".format(repr(key))
			elif value is not None:
				message = value

		if message is None:
			super().__init__(*args)
		else:
			super().__init__(message, *args)


class LibraryError(Exception):
	"""
	Base exception for `asab.LibraryService`.
	"""
	def __init__(self, *args) -> None:
		super().__init__(*args)


class LibraryInvalidPathError(LibraryError):
	"""
	Path in `asab.LibraryService` is invalid.
	"""
	def __init__(self, message="", path="", *args):
		self.Path = path
		message = "Invalid Library path '{}': {}".format(path, message)
		super().__init__(message, *args)


class LibraryNotReadyError(LibraryError):
	"""
	Raised when an operation is attempted on the LibraryService
	before all providers (or the library itself) are ready.

	Example Usage:
	try:
		async with library_service.open("/path/to/item") as item:
			if item is not None:
				data = item.read()
	except LibraryNotReadyError:
		print("Library is not ready yet.")
	"""
	def __init__(self, message="Library is not ready yet.", *args, **kwargs):
		super().__init__(message, *args, **kwargs)
