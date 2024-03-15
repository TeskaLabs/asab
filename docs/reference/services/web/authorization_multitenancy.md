# Authorization and multitenancy

The `asab.web.auth` module provides [authentication](https://en.wikipedia.org/wiki/Authentication) and
[authorization](https://en.wikipedia.org/wiki/Authorization) of incoming requests.
This enables your application to differentiate between users,
grant or deny them API access depending on their permissions, and work
with other relevant user data.

The module also implements [multitenancy](https://en.wikipedia.org/wiki/Multitenancy),
meaning that your application can be used by a number of independent subjects
(tenants, for example companies) without interfering with each other.

The `auth` module requires an authorization server to function.
It works best with TeskaLabs [Seacat Auth](https://github.com/TeskaLabs/seacat-auth)
authorization server 
(See [its documentation](https://docs.teskalabs.com/seacat-auth/getting-started/quick-start) for setup instructions).

## Getting started

To get started, initialize `AuthService` and install it in your `asab.web.WebContainer`:

``` python
class MyApplication(asab.Application):
	def __init__(self):
		super().__init__()

		# Initialize web container
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		# Initialize authorization service and install the decorators
		self.AuthService = asab.web.auth.AuthService(self)
		self.AuthService.install(self.WebContainer)
```

!!! note

	You may also need to specify your authorization server's `public_keys_url`
	(also known as `jwks_uri` in [OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8414#section-2)).
	In case you don't have any authorization server at hand,
	you can run the auth module in "mock mode". See the `configuration` section for details.


Every handler in `WebContainer` now accepts only requests with a valid authentication.
Unauthenticated requests are automatically answered with
[HTTP 401: Unauthorized](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401).
Authenticated requests will be inspected for user info, authorized user tenant and resources.
These attributes are passed to the handler method, if the method in question has
the corresponding keyword arguments (`user_info`, `tenant` and `resources`).
In the following example, the method will receive `user_info` and `resources` from the request:

``` python
async def order_breakfast(self, request, *, tenant, user_info, resources):
	user_id = user_info["sub"]
	user_name = user_info["preferred_username"]
	if "pancakes:eat" in resources:
		...
	return asab.web.rest.json_response(request, {
		"result": "Good morning {}, your breakfast will be ready in a minute!".format(user_name)
	})
```

See [examples/web-auth.py](https://github.com/TeskaLabs/asab/blob/master/examples/web-auth.py) for a full demo ASAB application with auth module.

## Configuration

The `asab.web.auth` module is configured
in the `[auth]` section with the following options:

| Option                | Type             | Meaning |
|-----------------------|------------------| --- |
| `public_keys_url`     | URL              | The URL of the authorization server's public keys (also known as `jwks_uri` in [OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8414#section-2)) |
| `enabled`             | boolean or `"mock"` | Enables or disables authentication and authorization or switches to mock authorization. In mock mode, all incoming requests are authorized with mock user info. There is no communication with the authorization server (so it is not necessary to configure `public_keys_url` in dev mode).
| `mock_user_info_path` | path             | Path to JSON file that contains user info claims used in mock mode. The structure of user info should follow the [OpenID Connect userinfo definition](https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse) and also contain the `resources` object.

Default options:

```ini
public_keys_url=http://localhost:3081/.well-known/jwks.json
enabled=yes
mock_user_info_path=/conf/mock-userinfo.json
```

## Multitenancy

### Strictly multitenant endpoints

Strictly multitenant endpoints always operate within a tenant, hence they need the `tenant` parameter to be always provided.
Such endpoints must define the `tenant` parameter in their **URL path** and include `tenant` argument in the handler method.
Auth service extracts the tenant from the URL path, validates the tenant existence,
checks if the request is authorized for the tenant, and finally passes the tenant name to the handler method.

!!! example "Example handler:"

	``` python
	class MenuHandler:
		def __init__(self, app):
			self.MenuService = app.get_service("MenuService")
			router = app.WebContainer.WebApp.router
			# Add a path with `tenant` parameter
			router.add_get("/{tenant}/todays-menu", self.get_todays_menu)

		# Define handler method with `tenant` argument in the signature
		async def get_todays_menu(self, request, *, tenant):
			menu = await self.MenuService.get_todays_menu(tenant)
			return asab.web.rest.json_response(request, data=menu)
	```

!!! example "Example request:"

	```
	GET http://localhost:8080/lazy-raccoon-bistro/todays-menu
	```


### Configurable multitenant endpoints

Configurable multitenant endpoints usually operate within a tenant, 
but they can also operate in tenantless mode if the application is designed for that. 

When you create an endpoint *without* `tenant` parameter in the URL path and *with* `tenant` argument in the 
handler method, the Auth service will either expect the `tenant` parameter to be provided in the **URL query**. 
If it is not in the query, the tenant variable is set to `None`.

!!! example "Example handler:"

	``` python
	class MenuHandler:
		def __init__(self, app):
			self.MenuService = app.get_service("MenuService")
			router = app.WebContainer.WebApp.router
			# Add a path without `tenant` parameter
			router.add_get("/todays-menu", self.get_todays_menu)

		# Define handler method with `tenant` argument in the signature
		async def get_todays_menu(self, request, *, tenant):
			menu = await self.MenuService.get_todays_menu(tenant)
			return asab.web.rest.json_response(request, data=menu)
	```

!!! example "Example requests:"

    ```
    GET http://localhost:8080/todays-menu?tenant=lazy-raccoon-bistro
    ```

## Mock mode

In mock mode, actual authorization is disabled and replaced with mock authorization, which is useful when you want 
to develop your ASAB application, but don't have any authorization server at hand. 
Activate mock mode by setting `enabled=mock` in the `[auth]` config section.
You can also specify a path to a JSON file with your own mock userinfo payload `[auth] mock_user_info_path`:

``` ini
[auth]
enabled=mock
mock_user_info_path=${THIS_DIR}/mock_userinfo.json
```

When dev mode is enabled, you don't have to provide `[public_keys_url]` since this option is ignored.

## Reference

::: asab.web.auth.AuthService


::: asab.web.auth.require

::: asab.web.auth.noauth
