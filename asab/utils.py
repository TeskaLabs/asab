def convert_to_seconds(value: str) -> float:
	"""
	Parse time duration string (e.g. "3h", "20m" or "1y") and convert it into seconds.
	"""
	value = value.replace(" ", "")

	try:
		# Second condition in each IF is for backward compatibility
		if value.endswith("ms"):
			value = float(value[:-2]) / 1000.0
		elif value.endswith("y") or value.endswith("Y"):
			value = float(value[:-1]) * 86400 * 365
		elif value.endswith("M"):
			value = float(value[:-1]) * 86400 * 31
		elif value.endswith("w") or value.endswith("W"):
			value = float(value[:-1]) * 86400 * 7
		elif value.endswith("d") or value.endswith("D"):
			value = float(value[:-1]) * 86400
		elif value.endswith("h"):
			value = float(value[:-1]) * 3600
		elif value.endswith("m"):
			value = float(value[:-1]) * 60
		elif value.endswith("s"):
			value = float(value[:-1])
		else:
			value = float(value)
	except ValueError as e:
		raise ValueError("'{}' is not a valid time specification: {}.".format(value, e))

	return value
