import aiohttp.web


class ASABError(Exception):
	"""
	Base class for ASAB errors that can be communicated to the client (in HTTP response or other)
	"""

	Prefix = "ASABError"

	def __init__(
		self,
		error_code: str,
		tech_message: str,
		error_i18n_key: str | None = None,
		error_dict: dict | None = None,
	):
		super().__init__(tech_message)
		self.ErrorCode = error_code
		self.TechMessage = tech_message
		self.ErrorDict = error_dict
		if error_i18n_key is not None:
			self.ErrorI18nKey = "{}|{}".format(self.Prefix, error_i18n_key)
		else:
			self.ErrorI18nKey = "{}|".format(self.Prefix)


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
