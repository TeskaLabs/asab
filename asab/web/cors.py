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


def normalize_origin(origin: str) -> str:
	"""
	Normalize an origin for comparison and for the `Access-Control-Allow-Origin` header.

	The scheme and host of an origin are case-insensitive (RFC 6454), so they are
	lowercased. A trailing slash is stripped because browsers and clients send both
	`https://app.example` and `https://app.example/`. The CORS `Origin` header never
	contains a path, query, or fragment; if one is present in the value it is left
	as-is and will simply not match an allowlist entry.

	Args:
		origin: An origin, for example `https://App.Example/`.

	Returns:
		The normalized origin, for example `https://app.example`.
	"""
	origin = origin.strip().rstrip("/")
	scheme, sep, rest = origin.partition("://")
	if sep:
		origin = "{}{}{}".format(scheme.lower(), sep, rest.lower())
	return origin


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
		self._RouteSet = set()
		self.AllowHeaders = ""
		self.AllowMethods = ""
		self.AllowCredentials = False
		self.AllowAll = False
		self.AllowedOrigins = set()
		self.OriginValidator = None
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
		allow_all, allowed_origins, origin_validator = self._parse_origin_policy(allow_origin)
		self.AllowAll = allow_all
		self.AllowedOrigins = allowed_origins
		self.OriginValidator = origin_validator
		self.AllowHeaders = normalize_header_list(allow_headers)
		self.AllowMethods = normalize_header_list(allow_methods)
		self.AllowCredentials = bool(allow_credentials)


	def add_paths(self, paths: typing.Union[str, typing.Iterable[str], None]):
		"""
		Add CORS path patterns. Duplicates are ignored.

		A path is a duplicate when its expanded route set is already covered by an
		existing entry. `/foo/*` expands to `/foo/{tail:.*}` and `/foo`, so adding
		`/foo` after `/foo/*` is a no-op, and adding `/foo/*` after `/foo` keeps
		both (`/foo/*` also covers sub-paths). This keeps `Paths` free of redundant
		entries while `_register_preflight_routes` stays idempotent.

		Args:
			paths: Path prefixes (`/foo/*`) and exact paths, or `None`.
		"""
		for path in normalize_path_list(paths):
			if path in self._PathSet:
				continue
			route_paths = {path_to_route(path)}
			if path.endswith("/*") and path != "/*":
				route_paths.add(path[:-2])
			if route_paths <= self._RouteSet:
				continue
			self._PathSet.add(path)
			self.Paths.append(path)
			self._RouteSet = self._RouteSet | route_paths


	def is_origin_allowed(self, origin: typing.Optional[str]) -> bool:
		"""
		Return whether `origin` is allowed by the current policy.

		Origins are compared in their normalized form: the scheme and host are
		case-insensitive and a trailing slash is ignored.

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
		return normalize_origin(origin) in self.AllowedOrigins


	def headers_for(
		self,
		origin: typing.Optional[str],
		path: str,
		request_headers: typing.Optional[str] = None,
		request_methods: typing.Optional[str] = None,
	) -> typing.Dict[str, str]:
		"""
		Return CORS headers for this request, or an empty dict if CORS must not apply.

		For preflight requests (OPTIONS with `Access-Control-Request-Headers` or
		`Access-Control-Request-Method`), the `Access-Control-Allow-Headers` and
		`Access-Control-Allow-Methods` values echo the intersection of what the
		request asked for and what the policy allows. This keeps the advertised
		list aligned with what the server actually accepts. On actual responses
		the configured lists are used unchanged.

		Args:
			origin: The request `Origin` header, or `None` if it is missing.
			path: The URL path of the request.
			request_headers: Value of the `Access-Control-Request-Headers` preflight
				header, or `None` for actual requests.
			request_methods: Value of the `Access-Control-Request-Method` preflight
				header, or `None` for actual requests.

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
			allow_origin = normalize_origin(origin)

		if request_headers is not None and self.AllowHeaders:
			allow_headers = _intersect_requested(request_headers, self.AllowHeaders)
		else:
			allow_headers = self.AllowHeaders

		if request_methods is not None and self.AllowMethods:
			allow_methods = _intersect_requested(request_methods, self.AllowMethods)
		else:
			allow_methods = self.AllowMethods

		headers = {
			"Access-Control-Allow-Origin": allow_origin,
			"Access-Control-Allow-Methods": allow_methods,
			"Access-Control-Allow-Headers": allow_headers,
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
		for name, value in self.headers_for(
			request.headers.get("Origin"),
			request.path,
			request.headers.get("Access-Control-Request-Headers"),
			request.headers.get("Access-Control-Request-Method"),
		).items():
			if name == "Vary":
				_merge_vary_origin(response.headers)
			else:
				response.headers[name] = value


	def _parse_origin_policy(
		self,
		allow_origin: typing.Union[str, typing.Iterable[str], typing.Callable[[str], bool]],
	) -> typing.Tuple[bool, typing.Set[str], typing.Optional[typing.Callable[[str], bool]]]:
		"""
		Parse an origin policy into its three runtime fields.

		This computes the complete policy without mutating the handler, so a
		`TypeError` from a bad value cannot leave the handler half-updated. The
		caller assigns the returned tuple in one step.

		Args:
			allow_origin: `"*"`, a string or iterable of origins, or a callable
				`origin: str -> bool`.

		Returns:
			A tuple `(allow_all, allowed_origins, origin_validator)`.
		"""
		parsed = parse_allow_origin(allow_origin)
		if callable(parsed):
			return False, set(), parsed
		if parsed == "*":
			return True, set(), None
		return False, set(normalize_origin(origin) for origin in split_config_list(parsed)), None


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


def _intersect_requested(requested: str, allowed: str) -> str:
	"""
	Return the tokens from `requested` that are present in `allowed`.

	Used for preflight responses: the browser asks for the headers or methods it
	will use via `Access-Control-Request-*`, and the server answers with the
	intersection so the advertised list never advertises more than the policy.

	Args:
		requested: Comma-separated tokens from the preflight request.
		allowed: Comma-separated tokens from the CORS policy.

	Returns:
		A comma-separated string of the tokens in `requested` that are in `allowed`,
		in the order requested. Empty if none are allowed.
	"""
	allowed_tokens = {token.strip().lower() for token in allowed.split(",") if token.strip()}
	result = []
	for token in requested.split(","):
		token = token.strip()
		if token and token.lower() in allowed_tokens:
			result.append(token)
	return ", ".join(result)


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
