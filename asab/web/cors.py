import re
import typing
import collections.abc


def split_config_list(
	value: typing.Union[str, typing.Iterable[str], None],
) -> typing.List[str]:
	"""
	Split a comma- and/or whitespace-separated config value into tokens.

	A string is split on commas and whitespace. An iterable of strings is flattened;
	each item is split the same way. `None` and a blank string yield an empty list.

	Args:
		value: A config string, an iterable of strings, or `None`.

	Returns:
		A list of non-empty tokens.
	"""
	if value is None:
		return []
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return []
		return [item for item in re.split(r"[,\s]+", value) if item]
	if isinstance(value, collections.abc.Iterable):
		tokens = []
		for item in value:
			if not isinstance(item, str):
				raise TypeError("Expected strings, not {}".format(type(item)))
			tokens.extend(split_config_list(item))
		return tokens
	raise TypeError("Expected a string or iterable of strings, not {}".format(type(value)))


def normalize_cors_config(value: typing.Optional[str]) -> str:
	"""
	Normalize the `[web] cors` origin policy.

	Args:
		value: The raw `[web] cors` string, or `None`.

	Returns:
		An empty string when CORS must not start, `*` when all origins are allowed,
		otherwise a comma-separated allowlist with no extra spaces.
	"""
	if value is None:
		return ""
	if not isinstance(value, str):
		raise TypeError("CORS config must be a string, not {}".format(type(value)))
	items = split_config_list(value)
	if not items:
		return ""
	if "*" in items:
		return "*"
	return ",".join(items)


def normalize_header_list(value: typing.Union[str, typing.Iterable[str], None]) -> str:
	"""
	Normalize Allow-Headers / Allow-Methods into a comma-separated header value.

	Args:
		value: A config string, an iterable of header or method names, or `None`.

	Returns:
		A comma-separated header value, or an empty string.
	"""
	return ", ".join(split_config_list(value))


def normalize_path_list(value: typing.Union[str, typing.Iterable[str], None]) -> typing.List[str]:
	"""
	Normalize preflight path patterns into a list of path strings.

	Args:
		value: A config string, an iterable of path patterns, or `None`.

	Returns:
		A list of path patterns.
	"""
	return split_config_list(value)


def path_to_route(path: str) -> str:
	"""
	Convert a trailing glob (`/foo/*`) into an aiohttp route pattern (`/foo/{tail:.*}`).

	Args:
		path: A CORS path pattern, possibly ending in `/*`.

	Returns:
		An aiohttp route pattern. Paths without a trailing glob are returned unchanged.
	"""
	path = path.strip()
	if path.endswith("/*"):
		return path[:-1] + "{tail:.*}"
	return path


def path_matches(request_path: str, patterns: typing.Iterable[str]) -> bool:
	"""
	Return True if `request_path` matches any CORS path pattern.

	A pattern ending in `/*` is a prefix (`/foo/*` matches `/foo` and `/foo/...`).
	Other patterns are exact.

	Args:
		request_path: The URL path of the request.
		patterns: CORS path patterns (`/foo/*` prefixes or exact paths).

	Returns:
		`True` if the path matches at least one pattern, otherwise `False`.
	"""
	for pattern in patterns:
		if _path_matches_pattern(request_path, pattern):
			return True
	return False


def parse_allow_origin(
	allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
) -> typing.Union[str, typing.Callable[[str], bool]]:
	"""
	Normalize an `enable_cors(allow_origin=...)` value to `*`, a comma-separated
	allowlist, an empty string, or a callable `origin -> bool`.

	Args:
		allow_origin: `"*"`, a string or iterable of origins, or a callable
			`origin: str -> bool`.

	Returns:
		`"*"` , a comma-separated allowlist, an empty string, or the callable unchanged.
	"""
	if isinstance(allow_origin, str):
		return normalize_cors_config(allow_origin)
	if callable(allow_origin):
		return allow_origin
	if isinstance(allow_origin, collections.abc.Iterable):
		parts = []
		for item in allow_origin:
			if not isinstance(item, str):
				raise TypeError("CORS origin values must be strings, not {}".format(type(item)))
			parts.append(item)
		return normalize_cors_config(",".join(parts))
	raise TypeError(
		"allow_origin must be '*', a string or iterable of origins, or a callable, not {}".format(
			type(allow_origin)
		)
	)


class CORSHandler:
	"""
	Origin, path, and header policy applied to both preflight and actual responses.
	"""

	def __init__(
		self,
		allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
		paths: typing.Union[str, typing.Iterable[str], None],
		allow_headers: typing.Union[str, typing.Iterable[str], None],
		allow_methods: typing.Union[str, typing.Iterable[str], None],
		allow_credentials: bool,
	):
		"""
		Create a CORS policy applied to both preflight and actual responses.

		Args:
			allow_origin: `"*"` to allow every origin, a string or iterable of allowed
				origins, or a callable `origin: str -> bool`.
			paths: Path prefixes (`/foo/*`) and exact paths that receive CORS headers.
			allow_headers: Allowed request headers.
			allow_methods: Allowed HTTP methods.
			allow_credentials: Whether browsers may send cookies and Authorization.
		"""
		self.Paths = []
		self._PathSet = set()
		self.set_policy(allow_origin, allow_headers, allow_methods, allow_credentials)
		self.add_paths(paths)


	def set_policy(
		self,
		allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
		allow_headers: typing.Union[str, typing.Iterable[str], None],
		allow_methods: typing.Union[str, typing.Iterable[str], None],
		allow_credentials: bool,
	):
		"""
		Replace the origin, header, method, and credentials policy.

		Args:
			allow_origin: `"*"` to allow every origin, a string or iterable of allowed
				origins, or a callable `origin: str -> bool`.
			allow_headers: Allowed request headers.
			allow_methods: Allowed HTTP methods.
			allow_credentials: Whether browsers may send cookies and Authorization.
		"""
		self._set_allow_origin(allow_origin)
		self.AllowHeaders = normalize_header_list(allow_headers)
		self.AllowMethods = normalize_header_list(allow_methods)
		self.AllowCredentials = bool(allow_credentials)


	def add_paths(self, paths: typing.Union[str, typing.Iterable[str], None]):
		"""
		Add CORS path patterns. Duplicates are ignored.

		Args:
			paths: Path prefixes (`/foo/*`) and exact paths, or `None`.
		"""
		for path in normalize_path_list(paths):
			if path not in self._PathSet:
				self._PathSet.add(path)
				self.Paths.append(path)


	def is_origin_allowed(self, origin: typing.Optional[str]) -> bool:
		"""
		Return whether `origin` is allowed by the current policy.

		Args:
			origin: The request `Origin` header, or `None` if it is missing.

		Returns:
			`True` if the origin is present and allowed, otherwise `False`.
		"""
		if not origin:
			return False
		if self.OriginValidator is not None:
			return bool(self.OriginValidator(origin))
		if self.AllowAll:
			return True
		return origin in self.AllowedOrigins


	def headers_for(self, origin: typing.Optional[str], path: str) -> typing.Dict[str, str]:
		"""
		Return CORS headers for this request, or an empty dict if CORS must not apply.

		Args:
			origin: The request `Origin` header, or `None` if it is missing.
			path: The URL path of the request.

		Returns:
			A mapping of CORS header names to values. Empty when the path is outside
			the configured patterns or the origin is missing or not allowed.
		"""
		if not path_matches(path, self.Paths):
			return {}
		if not self.is_origin_allowed(origin):
			return {}

		if self.AllowAll and not self.AllowCredentials:
			allow_origin = "*"
		else:
			# Echo the request origin. Never send `*` together with credentials.
			allow_origin = origin

		headers = {
			"Access-Control-Allow-Origin": allow_origin,
			"Access-Control-Allow-Methods": self.AllowMethods,
			"Access-Control-Allow-Headers": self.AllowHeaders,
			"Access-Control-Max-Age": "86400",
			"Vary": "Origin",
		}
		if self.AllowCredentials:
			headers["Access-Control-Allow-Credentials"] = "true"
		return headers


	def apply(self, request, response):
		"""
		Write CORS headers onto `response` when the request is allowed.

		`Vary: Origin` is merged into any existing `Vary` token list. `Vary: *` is
		left unchanged.

		Args:
			request: The incoming aiohttp request.
			response: The aiohttp response being prepared.
		"""
		for name, value in self.headers_for(request.headers.get("Origin"), request.path).items():
			if name == "Vary":
				_merge_vary_origin(response.headers)
			else:
				response.headers[name] = value


	def _set_allow_origin(
		self,
		allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
	):
		"""
		Replace only the origin policy.

		Args:
			allow_origin: `"*"`, a string or iterable of origins, or a callable
				`origin: str -> bool`.
		"""
		parsed = parse_allow_origin(allow_origin)
		if callable(parsed):
			self.AllowAll = False
			self.AllowedOrigins = set()
			self.OriginValidator = parsed
			return
		self.OriginValidator = None
		if parsed == "*":
			self.AllowAll = True
			self.AllowedOrigins = set()
			return
		self.AllowAll = False
		self.AllowedOrigins = set(split_config_list(parsed))


def _merge_vary_origin(headers) -> None:
	"""
	Add `Origin` to `Vary` without dropping existing tokens.

	`Vary: *` already varies on every header, including Origin, so it is left unchanged.

	Args:
		headers: A mutable mapping of response headers.
	"""
	existing = headers.get("Vary")
	if existing is None:
		headers["Vary"] = "Origin"
		return
	tokens = [token.strip() for token in existing.split(",") if token.strip()]
	if any(token == "*" for token in tokens):
		return
	if any(token.lower() == "origin" for token in tokens):
		return
	headers["Vary"] = "{}, Origin".format(existing.strip())


def _path_matches_pattern(request_path: str, pattern: str) -> bool:
	"""
	Return whether `request_path` matches a single CORS path pattern.

	Args:
		request_path: The URL path of the request.
		pattern: A `/foo/*` prefix or an exact path.

	Returns:
		`True` if the path matches the pattern, otherwise `False`.
	"""
	if pattern.endswith("/*"):
		prefix = pattern[:-1]  # "/foo/" or "/"
		if request_path.startswith(prefix):
			return True
		# `/foo/*` also matches the directory itself (`/foo`)
		return request_path == pattern[:-2]
	return request_path == pattern
