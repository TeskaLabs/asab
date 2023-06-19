.. currentmodule:: asab.web.auth

================================
Authentication and authorization
================================

:class:`AuthService` handles the authentication and authorization of incoming requests and extracts useful auth data in your handler methods.

Provides communication with authorization server and authenticates and authorizes requests.

Usage:

.. code:: python

    class MyApplication(asab.Application):
        def __init__(self):
            super().__init__()
            self.add_module(asab.web.Module)
            self.WebService = self.get_service("asab.WebService")
            self.WebContainer = asab.web.WebContainer(self.WebService, "web")

            # Initialize authorization service and install the decorators
            self.AuthService = asab.web.auth.AuthService(self)
            self.AuthService.install(self.WebContainer)

Installing the service allows you to use special keyword args in your handlers (``tenant``, ``user_info`` and ``resources``) that will be automatically filled in by the service, based on the request and its authorization.

Usage:

.. code:: python

    async def order_breakfast(self, request, *, tenant: str, user_info: dict, resources: frozenset):
        who = user_info["sub"]
        if "full-english:eat" in resources or "pancakes:eat" in resources:
            ...
        return asab.web.rest.json_response(request, {"result": "OK"})

`See full example here. <https://github.com/TeskaLabs/asab/blob/master/examples/web-auth.py>`__


Service configuration
=====================

In minimum **production** config, you need to specify at least the authorization server's ``public_keys_url``, for example:

.. code:: ini

    [auth]
    public_keys_url=http://localhost:8081/openidconnect/public_keys


In minimum **development** config, you can just activate the **dev mode**, in which the service does not need the above URLs configured:

.. code:: ini

    [auth]
    dev_mode=yes


Multitenancy
============

Strictly multitenant endpoints
------------------------------

Strictly multitenant endpoints always operate within a tenant, hence they need the `tenant` parameter to be always provided. Such endpoints must define the `tenant` parameter in their **URL path** and include `tenant` argument in the handler method. Auth service extracts the tenant from the URL path, validates the tenant existence, checks if the request is authorized for the tenant and finally passes the tenant name to the handler method.

Example handler:

.. code:: python

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

Example request:

.. code::

    GET http://localhost:8080/lazy-raccoon-bistro/todays-menu


Configurably multitenant endpoints
----------------------------------

Configurably multitenant endpoints usually operate within a tenant, but they can also operate in tenantless mode if the application is configured so. When you create an endpoint *without* ``tenant`` parameter in the URL path and *with* ``tenant`` argument in the handler method, the Auth service will either expect the ``tenant`` parameter to be provided in the **URL query** if mutlitenancy is enabled, or to not be provided at all if multitenancy is disabled. Use the ``multitenancy`` boolean switch in the ``[auth]`` config section to control the multitenancy setting.

- If ``multitenancy`` is **enabled**, the request's **query string** must include a tenant parameter. Requests without the tenant query result in Bad request (HTTP 400).
- If ``multitenancy`` is **disabled**, the tenant argument in the handler method is set to ``None``. Any ``tenant`` parameter in the query string is ignored.

Example handler:

.. code:: python

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

Example request (with multitenancy on):

.. code::

    GET http://localhost:8080/todays-menu?tenant=lazy-raccoon-bistro


Example request (with multitenancy off):

.. code::

    GET http://localhost:8080/todays-menu



Development mode
================

In dev mode, actual authorization is disabled and replaced with mock authorization. Useful for developing ASAB apps without authorization server. Activate by enabling ``dev_mode`` in the ``[auth]`` config section. You can also specify a path to a JSON file with your own mocked userinfo payload ``[auth] dev_user_info_path``:

```ini
[auth]
dev_mode=yes
dev_user_info_path=${THIS_DIR}/mock_userinfo.json
```

When dev mode is enabled, you don't have to provide `public_keys_url` as these options are ignored.



Reference
=========

AuthService
-----------
.. autoclass:: AuthService

    .. automethod:: install

        Applies authorization and

Handler decorators
------------------

Require
~~~~~~~
.. autofunction:: require

Sets resources that are required to access the endpoint. Requests that do not have these resources result in a ``HTTP 403 Forbidden`` response.

Usage:

.. code:: python

    @asab.web.auth.require("cake:access", "cake:eat")
    async def eat_cake(self, request, *, user_info):
        await CafeService.eat("cake", user=user_info["sub"])
        return asab.web.rest.json_response(request, {"result": "OK"})


.. autofunction:: noauth

Exempts the endpoint from authentication and authorization. No user info/tenants/resources are available in the handler method.

Usage:

.. code:: python

    @asab.web.auth.noauth
    async def drink_soda(self, request):
        await CafeService.drink("soda")
        return asab.web.rest.json_response(request, {"result": "OK"})
