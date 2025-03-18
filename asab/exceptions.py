import aiohttp.web


class ValidationError(Exception):
	"""
	Request cannot be processed because it does not match expected schema
	"""
	# TODO: Inherit from aiohttp.web.HTTPBadRequest
	pass


class NotAuthenticatedError(aiohttp.web.HTTPUnauthorized):
	"""
	Request could not be authenticated
	"""
	def __init__(self):
		# TODO: Optionally include "error", "realm" etc. (https://www.rfc-editor.org/rfc/rfc6750#section-3)
		super().__init__(headers={"WWW-Authenticate": "Bearer scope=openid"})


class AccessDeniedError(aiohttp.web.HTTPForbidden):
	"""
	Authenticated subject does not have the rights to access requested resource
	"""
	pass


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
		print("Library is not ready yet. Please try again later.")
	"""
	def __init__(self, message="Library is not ready yet.", *args, **kwargs):
		super().__init__(message, *args, **kwargs)
