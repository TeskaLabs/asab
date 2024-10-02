import contextvars

Tenant = contextvars.ContextVar("Tenant")
Authz = contextvars.ContextVar("Authz")
