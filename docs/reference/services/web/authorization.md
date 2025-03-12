# Authentication and authorization

The `asab.web.auth` module provides [authentication](https://en.wikipedia.org/wiki/Authentication) and
[authorization](https://en.wikipedia.org/wiki/Authorization) of incoming requests.
This enables your application to differentiate between users,
grant or deny them API access depending on their permissions, and work
with other relevant user data.

The `auth` module requires an authorization server to function.
It works best with TeskaLabs [Seacat Auth](https://github.com/TeskaLabs/seacat-auth)
authorization server 
(See [its documentation](https://docs.teskalabs.com/seacat-auth/getting-started/quick-start) for setup instructions).


## Getting started

To get started, add `asab.web` module to your application and initialize `asab.web.auth.AuthService`:

```python
import asab
import asab.web
import asab.web.auth

...

class MyApplication(asab.Application):
	def __init__(self):
		super().__init__()

		# Initialize web module
		asab.web.create_web_server(self)

		# Initialize authorization service
		self.AuthService = asab.web.auth.AuthService(self)
```

!!! note

	If your app has more than one web container, you will need to call `AuthService.install(web_container)` to apply 
    the authorization.


!!! note

	You may also need to specify your authorization server's `public_keys_url`
	(also known as `jwks_uri` in [OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8414#section-2)).
	In case you don't have any authorization server at hand,
	you can run the auth module in "mock mode". See the [Configuration section](#configuration) for details.


Every handler in your web server now accepts only requests with a valid authentication.
Unauthenticated requests are automatically answered with
[HTTP 401: Unauthorized](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401).
For every authenticated request, an `asab.web.auth.Authorization` object is created and stored 
in `asab.contextvars.Authz` for easy access.
It contains authorization and authentication details, such as `CredentialsId`, `Username` or `Email`, and 
access-checking methods `has_resource_access`, `require_superuser_access` and more ([see reference](#asab.web.auth.Authorization)).

```python
import asab.contextvars
import asab.web.rest

...

async def order_breakfast(request):
	authz = asab.contextvars.Authz.get()
	username = authz.Username

	# This will raise asab.exceptions.AccessDeniedError when the user is not authorized for resource `breakfast:access`
	authz.require_resource_access("breakfast:access")
	print("{} is ordering breakfast.".format(username))
    
	if authz.has_resource_access("breakfast:pancakes"):
		print("{} can get pancakes for breakfast!".format(username))
    
	if authz.has_superuser_access():
		print("{} can get anything they want!".format(username))

	return asab.web.rest.json_response(request, {
		"result": "Good morning {}, your breakfast will be ready in a minute!".format(username)
	})
```

See [examples/web-auth.py](https://github.com/TeskaLabs/asab/blob/master/examples/web-auth.py) for a full demo ASAB application with auth module.


## Multitenancy

If your web container runs in multi-tenant mode, AuthService will ensure the authorization of tenant context.
Read more in the [Multitenancy chapter](../multitenancy).


## Configuration

The `asab.web.auth` module is configured in the `[auth]` section with the following options:

| Option              | Type                                            | Meaning                                                                                                                                                                                                                                                                                                                                        |
|---------------------|-------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `enabled`           | `production` (default), `mock` or `development` | Switches authentication and authorization mode. In _mock_ mode all incoming requests are authorized with mock user info without any communication with the auth server. In _development_ mode the app is expected to run without Nginx reverse proxy and does auth introspection by itself (it is necessary to configure `introspection_url`). |
| `public_keys_url`   | URL                                             | The URL of the authorization server's public keys (also known as `jwks_uri` in [OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8414#section-2)                                                                                                                                                                                                   |
| `introspection_url` | URL                                             | The URL of Seacat Auth introspection endpoint used in development mode.                                                                                                                                                                                                                                                                        |
| `mock_claims_path`  | path                                            | Path to JSON file that contains auth claims (aka User Info) used in mock mode. The structure of the JSON object should follow the [OpenID Connect userinfo definition](https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse) and also contain the `resources` object.                                                        |

Default values:

```ini
enabled=production
public_keys_url=
introspection_url=
mock_claims_path=/conf/mock-claims.json
```

### Production mode

In production mode, the `AuthService` uses the authorization server to authenticate and authorize incoming requests.
The application is expected to run behind Nginx reverse proxy with auth introspection enabled.

You need to configure `public_keys_url` to point to the auth server's public keys endpoint to be able to verify incoming requests.

```ini
[auth]
public_keys_url=https://example.teskalabs.com/.well-known/jwks.json
```

#### Internal auth

To use ASAB's cluster-internal authentication (together with the web authentication above), 
initialize `asab.api.ApiService` and `asab.zookeeper.Module` in your application.
This will automatically set up shared keys necessary for internal auth, no extra configuration necessary.

You can also use internal authentication without web authentication by leaving `public_keys_url` empty.


### Development mode

In development mode, the `AuthService` expects the application to run without Nginx reverse proxy and 
does auth token introspection by itself.

To use the development mode, set the `enabled` option to `development` and specify 
the `introspection_url` to point to the auth server's access token introspection endpoint.
You also need to configure `public_keys_url` to the auth server's public keys endpoint.

```ini
[auth]
enabled=development
public_keys_url=http://localhost:8900/.well-known/jwks.json
introspection_url=http://localhost:8900/nginx/introspect/openidconnect
```

### Mock mode

In mock mode, the `AuthService` authorizes all incoming requests with mock authorization claims (aka User Info) without 
any communication with the auth server.
You can also customize the claims by providing a path to a JSON file with mock claims.
The file content should comply with the [OpenID Connect userinfo response definition](https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse) 
and also contain the `resources` object.

```ini
[auth]
enabled=mock
mock_claims_path=./mock-claims.json
```


## Reference

::: asab.web.auth.AuthService


::: asab.web.auth.Authorization


::: asab.web.auth.require

::: asab.web.auth.require_superuser

::: asab.web.auth.noauth
