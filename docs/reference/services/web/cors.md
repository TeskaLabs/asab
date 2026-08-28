# Cross-Origin Resource Sharing (CORS)

!!! tip

	[This article](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) explains the key concept of CORS very well.

The Cross-Origin Resource Sharing standard works by adding HTTP headers that let servers describe which origins are permitted to read a response from a web browser. For HTTP methods that can cause side-effects (in particular methods other than **GET**, or **POST** with certain MIME types), the specification mandates that browsers **"preflight"** the request with **OPTIONS**, and only then send the actual request. Servers can also tell clients whether "credentials" (cookies and HTTP authentication) should be sent with requests.

ASAB applies the same origin, methods, headers, and credentials policy to preflight (**OPTIONS**) and to actual responses. CORS is installed only on paths listed in `cors_preflight_paths` (or passed to `enable_cors()`). Auth and tenant wrappers skip **OPTIONS** so preflight is not blocked by authentication.

If the request has no `Origin` header, or the origin is not allowed, CORS headers are omitted. Untrusted origins are never echoed. A preflight request still receives **204 No Content**.


## Configuration

CORS starts automatically when `[web] cors` is non-empty. Leave it empty if the application will call [`WebContainer.enable_cors()`](#asab.web.WebContainer.enable_cors) from code.

``` ini
[web]
cors=*
cors_preflight_paths=/*
cors_allow_headers=Authorization, Content-Type, X-App, X-Request-Id
cors_allow_methods=GET, POST, PUT, PATCH, DELETE, OPTIONS
cors_allow_credentials=no
```

| Option | Meaning |
| --- | --- |
| `cors` | Origin policy. Empty (the default) does not start CORS. `*` allows every origin. Otherwise a comma- and/or whitespace-separated allowlist of origins, normalized to comma-separated values with no extra spaces. If the list contains `*`, it is treated as `*`. |
| `cors_preflight_paths` | Path prefixes (`/foo/*`) and exact paths that receive CORS headers, including OPTIONS preflight. Values must start with `"/"`. The default `/*` covers the whole application. |
| `cors_allow_headers` | Value of `Access-Control-Allow-Headers`. |
| `cors_allow_methods` | Value of `Access-Control-Allow-Methods`. |
| `cors_allow_credentials` | When `yes`, responses include `Access-Control-Allow-Credentials: true`. |

### Credentials and `*`

Browsers reject `Access-Control-Allow-Origin: *` together with `Access-Control-Allow-Credentials: true`. When `cors` is `*` (or `allow_origin="*"`) **and** credentials are enabled, ASAB echoes the request `Origin` instead of sending `*`. That allows any origin to make a credentialed request. Turn credentials off if you want a true wildcard (`Access-Control-Allow-Origin: *`).


## Preflight paths

Preflight requests use the **OPTIONS** method on the same path as the actual request. Use `cors_preflight_paths` (or the `preflight_paths` argument of `enable_cors()`) to list those paths, separated by comma and/or whitespace.

A trailing glob is a prefix: `/foo/*` matches `/foo` and everything under `/foo/`. Other entries are exact paths. The glob is converted to an aiohttp route (`/foo/{tail:.*}`) only when registering OPTIONS, not by replacing `*` in the whole config string.

``` ini
[web]
cors=*
cors_preflight_paths=/api/*, /.well-known/openid-configuration
```


## Enabling CORS from code

Applications that decide allowed origins at runtime (for example SeaCat Auth checking registered clients) should leave `[web] cors` empty and call `enable_cors()`:

``` python
container.enable_cors(
	allow_origin=client_svc.is_origin_allowed,
	preflight_paths=[
		"/openidconnect/*",
		"/.well-known/openid-configuration",
		"/.well-known/oauth-authorization-server",
		"/.well-known/jwks.json",
		"/.well-known/oauth-protected-resource",
		"/.well-known/oauth-protected-resource/*",
	],
	allow_headers=["Authorization", "Content-Type", "X-App", "X-Request-Id"],
	allow_credentials=True,
)
```

`allow_origin` is a required argument. It may be `"*"`, a string or iterable of origins (parsed like `[web] cors`), or a synchronous callable `origin: str -> bool`.

If `enable_cors()` is called again (for example after config started CORS with `*`, then the application installs a validator), the origin policy is **replaced** and any new preflight paths are **added**. The same OPTIONS route is not registered twice.


## Reference

::: asab.web.WebContainer.enable_cors

::: asab.web.WebContainer.add_preflight_handlers
