# Multitenancy

This module implements [multitenancy](https://en.wikipedia.org/wiki/Multitenancy),
meaning that your application can be used by a number of independent subjects
(tenants, for example companies) without interfering with each other.


## Getting started

To set up an **application with multi-tenant web interface**, create an application with a web server and initialize `asab.web.tenant.TenantService`.
Tenant service automatically tries to install tenant context wrapper to your web handlers, which enables you to access the request's tenant context using `asab.contextvars.Tenant.get()`.

```python
import asab
import asab.web
import asab.web.tenant
import asab.contextvars

class MyApplication(asab.Application):
	def __init__(self):
		super().__init__()

		# Initialize web module
		asab.web.create_web_server(self)

		# Initialize tenant service
		self.TenantService = asab.web.tenant.TenantService(self)
```

!!! note

	If your app has more than one web container, you will need to call `TenantService.install(web_container)` to apply the tenant context wrapper.

This also adds the requirement for `tenant` parameter in the URL of every request - either in the path or in the query.


### Mandatory tenant in path

If **tenant context is mandatory** for your endpoint, it is recommended to require the `tenant` parameter in the URL path, such as:

```python
import asab
import asab.web
import asab.web.tenant
import asab.contextvars

class NotesApplication(asab.Application):
	def __init__(self):
		super().__init__()
		web = asab.web.create_web_server(self)
		tenant_svc = asab.web.tenant.TenantService(self)

		web.add_get("/{tenant}/note", self.list_notes)  # Tenant parameter required in path
        
	async def list_notes(self, request):
		tenant = asab.contextvars.Tenant.get()
		print("Requesting notes for tenant {!r}...".format(tenant))
```

!!! note

	It is a good practice to have `tenant` as the first component of the URL path if possible.


### Mandatory tenant in query

When the tenant context is mandatory for your endpoint, but it is not feasible to have the tenant parameter hard-baked into the path, define your endpoint path without the `tenant` path parameter.
The handler with require `tenant` to be present in the URL query.
Requests without the required parameter will result in `aiohttp.web.HTTPNotFound` (HTTP 404).

```python
import asab
import asab.web
import asab.web.tenant
import asab.contextvars

class NotesApplication(asab.Application):
	def __init__(self):
		super().__init__()
		web = asab.web.create_web_server(self)
		tenant_svc = asab.web.tenant.TenantService(self)

		web.add_get("/note", self.list_notes)  # No tenant parameter in path!
        
	async def list_notes(self, request):
		tenant = asab.contextvars.Tenant.get()
		print("Requesting notes for tenant {!r}...".format(tenant))
```


### Optional tenant in query

When the **tenant context is optional** for your endpoint (or when the endpoint does not use tenants at all), define its path without the `tenant` parameter in path and decorate the method handler with `@asab.web.tenant.allow_no_tenant`.
Requests without the `tenant` parameter will have their Tenant context set to `None`.

```python
import asab
import asab.web
import asab.web.tenant
import asab.contextvars

class NotesApplication(asab.Application):
	def __init__(self):
		super().__init__()
		web = asab.web.create_web_server(self)
		tenant_svc = asab.web.tenant.TenantService(self)

		web.add_get("/{tenant}/note", self.list_notes)  # No tenant parameter in path!
        
	@asab.web.tenant.allow_no_tenant  # Allow requests with undefined tenant!
	async def list_notes(self, request):
		tenant = asab.contextvars.Tenant.get()
		if tenant is None:
			print("Requesting notes without any tenant. Not sure what to do...")
		else:
			print("Requesting notes for tenant {!r}...".format(tenant))
```


## Working with known tenants

When you provide `tenant_url` or tenant `ids` in the configuration, TenantService will make the set of known tenants available through its `Tenants` property.
You can also make use of the `TenantService.is_tenant_known(tenant)` method.


!!! note

    If you only want to use the service to access known tenants and do not need the web middleware, initialize TenantService with `set_up_web_wrapper` argument set to `False`.


## Configuration

The `asab.web.tenant` module is configured in the `[tenants]` section with the following options:

| Option       | Type            | Meaning                                                  |
|--------------|-----------------|----------------------------------------------------------|
| `ids`        | List of strings | (Optional) Known tenant IDs.                             |
| `tenant_url` | URL             | (Optional) Location of a JSON array of known tenant IDs. |


## Reference

::: asab.web.tenant.TenantService

::: asab.web.tenant.allow_no_tenant
