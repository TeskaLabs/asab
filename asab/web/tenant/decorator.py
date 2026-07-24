def allow_no_tenant(handler):
	"""
	Allow receiving requests without tenant parameter.

	Args:
		handler: Web handler method

	Returns:
		The same handler, marked so tenant middleware permits missing tenant.

	Examples:
		>>> import asab.web.rest
		>>> import asab.web.tenant
		>>> import asab.contextvars
		>>>
		>>> @asab.web.tenant.allow_no_tenant
		>>> async def info(self, request):
		>>> 	tenant = asab.contextvars.Tenant.get()
		>>> 	if tenant is None:
		>>> 		print("The request does not have a tenant and that's fine.")
		>>> 	else:
		>>> 		print("The request has tenant {!r}.".format(tenant))
	"""
	handler.AllowNoTenant = True
	return handler
