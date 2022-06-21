class ValidationError(Exception):
	pass


class Conflict(Exception):
	# TODO: Handle when the value of `key` or `value` is `None`
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
