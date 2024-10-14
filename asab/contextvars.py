import contextvars

Tenant = contextvars.ContextVar("Tenant")

# Contains aiohttp.web.Request
Request = contextvars.ContextVar("Request")
