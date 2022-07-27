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


def validate_url(url: str, schema):
	# Remove leading and trailing whitespaces
	url = url.strip()

	if url.endswith("/"):
		url = url[:-1]

	if schema is None:  # Schema doesn't get checked
		return url
	elif type(schema) is tuple:  # Supports tuple
		if url.split("://")[0] in schema:
			return url
	elif "://" in url and schema == url.split("://")[0]:
		return url
	else:
		if "://" in url:
			raise ValueError("{} has an invalid schema: {}".format(url, url.split("://")[0]))
		elif "://" not in url:
			raise ValueError("{} does not have a schema".format(url))
		else:
			raise ValueError("{} has an invalid schema".format(url))
	return url
