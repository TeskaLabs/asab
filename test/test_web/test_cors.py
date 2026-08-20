import unittest

from asab.web.cors import (
	CORSHandler,
	normalize_cors_config,
	normalize_header_list,
	normalize_path_list,
	path_matches,
	path_to_route,
)


class _Request(object):
	def __init__(self, path, origin=None):
		self.path = path
		self.headers = {}
		if origin is not None:
			self.headers["Origin"] = origin


class _Response(object):
	def __init__(self):
		self.headers = {}


def _handler(**kwargs):
	defaults = dict(
		allow_origin="*",
		paths=["/*"],
		allow_headers="Authorization, Content-Type, X-App, X-Request-Id",
		allow_methods="GET, POST, PUT, PATCH, DELETE, OPTIONS",
		allow_credentials=True,
	)
	defaults.update(kwargs)
	return CORSHandler(**defaults)


class TestNormalizeCorsConfig(unittest.TestCase):

	def test_empty_disables_cors(self):
		self.assertEqual(normalize_cors_config(""), "")
		self.assertEqual(normalize_cors_config("   "), "")
		self.assertEqual(normalize_cors_config("\n"), "")
		self.assertFalse(normalize_cors_config(""))

	def test_star(self):
		self.assertEqual(normalize_cors_config("*"), "*")
		self.assertEqual(normalize_cors_config("  *  "), "*")

	def test_mixed_separators_become_comma_separated(self):
		self.assertEqual(
			normalize_cors_config("https://a.example https://b.example, https://c.example"),
			"https://a.example,https://b.example,https://c.example",
		)

	def test_star_in_list_is_star(self):
		self.assertEqual(normalize_cors_config("https://a.example, *"), "*")
		self.assertEqual(normalize_cors_config("* https://a.example"), "*")

	def test_newlines_and_many_items(self):
		# Old code passed re.MULTILINE (value 8) as maxsplit, truncating longer lists.
		value = "\n".join(["https://o{}.example".format(i) for i in range(12)])
		self.assertEqual(
			normalize_cors_config(value),
			",".join(["https://o{}.example".format(i) for i in range(12)]),
		)


class TestNormalizeLists(unittest.TestCase):

	def test_header_list_from_string_and_iterable(self):
		self.assertEqual(
			normalize_header_list("Authorization, Content-Type, X-App, X-Request-Id"),
			"Authorization, Content-Type, X-App, X-Request-Id",
		)
		self.assertEqual(
			normalize_header_list(["Authorization", "Content-Type"]),
			"Authorization, Content-Type",
		)
		self.assertEqual(normalize_header_list("GET,POST,PUT"), "GET, POST, PUT")

	def test_path_list_split_without_global_star_replace(self):
		self.assertEqual(
			normalize_path_list("/openidconnect/*, /.well-known/openid-configuration"),
			["/openidconnect/*", "/.well-known/openid-configuration"],
		)
		self.assertEqual(
			normalize_path_list(["/foo/*", "/bar"]),
			["/foo/*", "/bar"],
		)
		self.assertEqual(len(normalize_path_list("/a/*, /b/*, /c/*, /d/*, /e/*, /f/*, /g/*, /h/*, /i/*")), 9)


class TestPathGlob(unittest.TestCase):

	def test_path_to_route_trailing_glob_only(self):
		self.assertEqual(path_to_route("/foo/*"), "/foo/{tail:.*}")
		self.assertEqual(path_to_route("/*"), "/{tail:.*}")
		self.assertEqual(path_to_route("/.well-known/jwks.json"), "/.well-known/jwks.json")

	def test_star_inside_path_is_not_a_glob(self):
		# Conversion is per path, not a global replace of every '*'
		self.assertEqual(path_to_route("/foo/*/bar"), "/foo/*/bar")

	def test_prefix_and_exact_matching(self):
		self.assertTrue(path_matches("/foo/bar", ["/foo/*"]))
		self.assertTrue(path_matches("/foo", ["/foo/*"]))
		self.assertTrue(path_matches("/foo/", ["/foo/*"]))
		self.assertFalse(path_matches("/foobar", ["/foo/*"]))
		self.assertTrue(path_matches("/exact", ["/exact"]))
		self.assertFalse(path_matches("/exact/more", ["/exact"]))
		self.assertTrue(path_matches("/anything", ["/*"]))
		self.assertTrue(path_matches("/", ["/*"]))

	def test_path_isolation(self):
		patterns = ["/openidconnect/*", "/.well-known/openid-configuration"]
		self.assertTrue(path_matches("/openidconnect/authorize", patterns))
		self.assertTrue(path_matches("/.well-known/openid-configuration", patterns))
		self.assertFalse(path_matches("/.well-known/jwks.json", patterns))
		self.assertFalse(path_matches("/asab/v1/info", patterns))


class TestCORSHandler(unittest.TestCase):

	def test_missing_origin_omits_headers(self):
		handler = _handler(allow_origin="*")
		self.assertEqual(handler.headers_for(None, "/hello"), {})
		self.assertEqual(handler.headers_for("", "/hello"), {})

	def test_star_with_credentials_echoes_origin(self):
		handler = _handler(allow_origin="*", allow_credentials=True)
		origin = "https://app.example"
		headers = handler.headers_for(origin, "/hello")
		self.assertEqual(headers["Access-Control-Allow-Origin"], origin)
		self.assertEqual(headers["Access-Control-Allow-Credentials"], "true")
		self.assertNotEqual(headers["Access-Control-Allow-Origin"], "*")
		self.assertEqual(headers["Vary"], "Origin")
		self.assertEqual(headers["Access-Control-Max-Age"], "86400")
		self.assertIn("GET", headers["Access-Control-Allow-Methods"])
		self.assertIn("Authorization", headers["Access-Control-Allow-Headers"])
		self.assertNotIn("X-PINGOTHER", headers["Access-Control-Allow-Headers"])

	def test_star_without_credentials_sends_star(self):
		handler = _handler(allow_origin="*", allow_credentials=False)
		headers = handler.headers_for("https://app.example", "/hello")
		self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
		self.assertNotIn("Access-Control-Allow-Credentials", headers)

	def test_static_allowlist_allow_and_deny(self):
		handler = _handler(
			allow_origin="https://a.example https://b.example",
			allow_credentials=True,
		)
		allowed = handler.headers_for("https://a.example", "/hello")
		self.assertEqual(allowed["Access-Control-Allow-Origin"], "https://a.example")
		self.assertEqual(handler.headers_for("https://evil.example", "/hello"), {})

		handler = _handler(allow_origin=["https://a.example", "https://b.example"])
		self.assertTrue(handler.is_origin_allowed("https://b.example"))
		self.assertFalse(handler.is_origin_allowed("https://c.example"))

	def test_callback_allow_and_deny(self):
		allowed = {"https://client.example"}

		def is_origin_allowed(origin):
			return origin in allowed

		handler = _handler(allow_origin=is_origin_allowed, allow_credentials=True)
		ok = handler.headers_for("https://client.example", "/openidconnect/token")
		self.assertEqual(ok["Access-Control-Allow-Origin"], "https://client.example")
		self.assertEqual(ok["Access-Control-Allow-Credentials"], "true")
		self.assertEqual(handler.headers_for("https://other.example", "/openidconnect/token"), {})

	def test_path_isolation_omits_cors_outside_patterns(self):
		handler = _handler(
			allow_origin="*",
			paths=["/openidconnect/*", "/.well-known/openid-configuration"],
		)
		origin = "https://app.example"
		self.assertTrue(handler.headers_for(origin, "/openidconnect/authorize"))
		self.assertTrue(handler.headers_for(origin, "/.well-known/openid-configuration"))
		self.assertEqual(handler.headers_for(origin, "/asab/v1/info"), {})
		self.assertEqual(handler.headers_for(origin, "/.well-known/jwks.json"), {})

	def test_preflight_and_actual_share_policy(self):
		handler = _handler(
			allow_origin=["https://a.example"],
			allow_headers=["Authorization", "Content-Type"],
			allow_methods=["GET", "POST", "OPTIONS"],
			allow_credentials=True,
		)
		origin = "https://a.example"
		preflight = handler.headers_for(origin, "/api/item")
		actual = handler.headers_for(origin, "/api/item")
		self.assertEqual(preflight, actual)

	def test_replace_origin_policy_and_add_paths(self):
		handler = _handler(allow_origin="*", paths=["/*"])
		self.assertTrue(handler.is_origin_allowed("https://any.example"))

		def only_app(origin):
			return origin == "https://app.example"

		handler.set_policy(
			only_app,
			handler.AllowHeaders,
			handler.AllowMethods,
			handler.AllowCredentials,
		)
		handler.add_paths(["/openidconnect/*"])

		self.assertFalse(handler.is_origin_allowed("https://any.example"))
		self.assertTrue(handler.is_origin_allowed("https://app.example"))
		self.assertEqual(handler.Paths, ["/*", "/openidconnect/*"])

	def test_apply_writes_headers_on_response(self):
		handler = _handler(allow_origin="https://a.example", allow_credentials=True)
		response = _Response()
		handler.apply(_Request("/hello", "https://a.example"), response)
		self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://a.example")

		denied = _Response()
		handler.apply(_Request("/hello", "https://evil.example"), denied)
		self.assertEqual(denied.headers, {})

		no_origin = _Response()
		handler.apply(_Request("/hello"), no_origin)
		self.assertEqual(no_origin.headers, {})
