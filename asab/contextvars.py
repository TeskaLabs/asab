import contextvars
import contextlib

# Contains tenant ID string
Tenant = contextvars.ContextVar("Tenant")

# Contains asab.web.auth.Authorization object
Authz = contextvars.ContextVar("Authz")

# Contains aiohttp.web.Request
Request = contextvars.ContextVar("Request")


def get_current_tenant_id():
	"""
	Return current tenant from auth context, or None if not present.
	"""
	return Tenant.get(None)


def get_current_credentials_id():
	"""
	Return current credentials ID from auth context, or None if not present.
	"""
	authz = Authz.get(None)
	return getattr(authz, "CredentialsId", None)


@contextlib.contextmanager
def tenant_context(tenant):
	tenant_ctx = Tenant.set(tenant)
	try:
		yield tenant
	finally:
		Tenant.reset(tenant_ctx)
