import contextvars

# Contains tenant ID string
Tenant = contextvars.ContextVar("Tenant")

# Contains asab.web.auth.Authorization object
Authz = contextvars.ContextVar("Authz")
