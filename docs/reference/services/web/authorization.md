# Authorization

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

The `asab.web.auth` module is configured
in the `[auth]` section with the following options:

| Option | Type | Meaning |
| --- | --- | --- |
| `public_keys_url` | URL | The URL of the authorization server's public keys (also known as `jwks_uri` in [OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8414#section-2) |
| `enabled` | boolean or `"mock"` | Enables or disables authentication and authorization or switches to mock authorization. In mock mode, all incoming requests are authorized with mock user info. There is no communication with the authorization server (so it is not necessary to configure `public_keys_url` in dev mode). |
| `mock_user_info_path` | path | Path to JSON file that contains user info claims used in mock mode. The structure of user info should follow the [OpenID Connect userinfo definition](https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse) and also contain the `resources` object. |

Default options:

```ini
public_keys_url=http://localhost:3081/.well-known/jwks.json
enabled=yes
mock_user_info_path=/conf/mock-userinfo.json
```


## Reference

::: asab.web.auth.AuthService


::: asab.web.auth.Authorization


::: asab.web.auth.require

::: asab.web.auth.require_superuser

::: asab.web.auth.noauth
