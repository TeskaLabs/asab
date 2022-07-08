class ValidationError(Exception):
	"""
	Request cannot be processed because it does not match expected schema
	"""
	pass


class Conflict(Exception):
	"""
	Request cannot be satisfied because it would introduce a state that violates some uniqueness requirement
	"""
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
