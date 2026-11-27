from asab.contextvars import Tenant


def get_current_tenant_id(self):
	"""
	Return current tenant from auth context, or None if not present.
	"""
	try:
		return Tenant.get()
	except LookupError:
		return None
