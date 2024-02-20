# contextvars.py
from contextvars import ContextVar

# Define a context variable for tenant
tenant_var = ContextVar('tenant', default=None)
