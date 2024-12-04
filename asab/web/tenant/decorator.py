import functools


def allow_no_tenant(handler):
	"""
	Allow receiving requests without tenant parameter.

	Args:
		handler: Web handler method

	Returns:
		Wrapped web handler that allows requests with undefined tenant.
	"""
	handler.AllowNoTenant = True

	@functools.wraps(handler)
	async def _allow_no_tenant_wrapper(*args, **kwargs):
		return await handler(*args, **kwargs)

	return _allow_no_tenant_wrapper
