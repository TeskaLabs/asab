import os
import urllib.parse
import configparser
import typing


def convert_to_seconds(value: str) -> float:
	"""
	Parse time duration string (e.g. "3h", "20m" or "1y") and convert it into seconds.

	Args:
		value: Time duration string.

	Returns:
		float: Number of seconds.

	Raises:
		ValueError: If the string is not in a valid format.
	"""
	if isinstance(value, (int, float)):
		return float(value)

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


def convert_to_bytes(size: str) -> int:
	"""
	Convert a size string to bytes. The size string should be a number
	optionally followed by a unit (B, kB, MB, GB, or TB), e.g., "10MB".

	Examples:
		Configuration:
		```ini
		[general]
		rotate_size=30G
		```
		Usage:
		```python
		self.RotateAtSize = asab.utils.convert_to_bytes(asab.Config.get('general', 'rotate_size'))
		```

	Args:
		size: Size string.

	Returns:
		Size in bytes.

	Raises:
		ValueError: If the size string does not have the correct format.
	"""
	units = {
		"B": 1,

		"kB": 10**3,
		"MB": 10**6,
		"GB": 10**9,
		"TB": 10**12,

		# These are typical shortcuts that users take, we support them as well
		"k": 10**3,
		"K": 10**3,
		"M": 10**6,
		"G": 10**9,
		"T": 10**12,

	}
	size = size.strip()  # remove leading and trailing whitespace

	if size.isdigit():
		# size is just a number, so it's already in bytes
		return int(size)

	# size has a unit, find where the number part ends
	for i, char in enumerate(size):
		if not char.isdigit() and char != '.':
			break
	else:
		# no unit found
		raise ValueError("Invalid size string: {}".format(size))

	number = size[:i]
	unit = size[i:].strip()

	if unit not in units:
		raise ValueError("Invalid unit: {}".format(unit))

	return int(float(number) * units[unit])


def string_to_boolean(value: str) -> bool:
	"""
	Convert common boolean string values (e.g. 'yes' or 'no') into boolean.

	- `True`: `1`, `'yes'`, `'true'`, `'on'`
	- `False`: `0`, `'no'`, `'false'`, `'off'`

	Args:
		value: A value to be parsed.

	Returns:
		Value converted to bool.
	"""
	if isinstance(value, bool):
		return value
	if value.lower() not in configparser.ConfigParser.BOOLEAN_STATES:
		raise ValueError("Not a boolean: {}".format(value))
	return configparser.ConfigParser.BOOLEAN_STATES[value.lower()]


def validate_url(input_url: str, scheme: typing.Union[str, typing.Tuple[str], None]) -> str:
	"""Parse URL, remove leading and trailing whitespaces and a trailing slash.
	If `scheme` is specified, check if it matches the `input_url` scheme.

	Args:
		input_url (str): URL to be parsed and validated.
		scheme (str | tuple[str] | None): Requested URL schema.

	Raises:
		ValueError: If `scheme` is specified and is invalid.

	Returns:
		str: Parsed and validated URL.
	"""
	# Remove leading and trailing whitespaces before parsing
	url = urllib.parse.urlparse(input_url.strip())

	if url.path.endswith("/"):
		url = url._replace(path=url.path[:-1])

	if scheme is None:  # Scheme doesn't get checked
		return url.geturl()
	elif isinstance(scheme, tuple):  # Supports tuple
		if url.scheme in scheme:
			return url.geturl()
	elif scheme == url.scheme:
		return url.geturl()
	else:
		if url.scheme:
			raise ValueError("'{}' has an invalid scheme: '{}'".format(url.geturl(), url.scheme))
		elif not url.scheme:
			raise ValueError("'{}' does not have a scheme".format(url.geturl()))
		else:
			raise ValueError("'{}' has an invalid scheme".format(url.geturl()))
	return url.geturl()


def running_in_container() -> bool:
	"""
	Check if the application is running in Docker or Podman container.

	Returns:
		bool: `True` if the application is running in a container.
	"""

	# The process ID is 1 only in the docker/podman container
	if os.getpid() == 1:
		return True

	# This works for older versions of Ubuntu with cgroups v1 and Docker
	if os.path.exists('/.dockerenv') and os.path.isfile('/proc/self/cgroup'):
		with open('/proc/self/cgroup', "r") as f:
			if any('docker' in line for line in f.readlines()):
				return True

	# Since Ubuntu 22.04 linux kernel uses cgroups v2 which do not operate with /proc/self/cgroup file
	# Works only for "overlay" filesystem.
	if os.path.isfile('/proc/self/mountinfo'):
		with open('/proc/self/mountinfo', "r") as f:
			for line in f.readlines():
				# Seek for a root filesystem
				if ' / / ' not in line:
					continue

				# Is the root filesystem overlay?
				if ' overlay ' not in line:
					continue

				return True

	return False
