import contextvars
import contextlib

# Contains tenant ID string
Tenant = contextvars.ContextVar("Tenant")

# Contains asab.web.auth.Authorization object
Authz = contextvars.ContextVar("Authz")

# Contains aiohttp.web.Request
Request = contextvars.ContextVar("Request")


@contextlib.contextmanager
def tenant_context(tenant):
	tenant_ctx = Tenant.set(tenant)
	try:
		yield tenant
	finally:
		Tenant.reset(tenant_ctx)
