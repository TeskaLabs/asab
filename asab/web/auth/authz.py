import typing


SUPERUSER_RES_ID = "authz:superuser"


class Authorization:
	"""
	Contains authentication and authorization details, provides methods for checking access control
	"""
	def __init__(self, auth_service, userinfo: dict, tenant: typing.Union[str, None]):
		self.AuthService = auth_service
		self.Userinfo = userinfo
		self.CredentialsId = userinfo.get("sub")
		self.Username = userinfo.get("preferred_username") or userinfo.get("username")
		self.Email = userinfo.get("email")
		self.Phone = userinfo.get("phone")

		self.Tenant = tenant

	def has_superuser_access(self):
		if not self.AuthService.is_enabled():
			return True
		return has_superuser_access(self.Userinfo)

	def has_resource_access(self, resource_id: str | typing.Iterable[str]):
		if not self.AuthService.is_enabled():
			return True
		if isinstance(resource_id, str):
			return has_resource_access(self.Userinfo, {resource_id}, tenant=self.Tenant)
		else:
			return has_resource_access(self.Userinfo, resource_id, tenant=self.Tenant)


def has_superuser_access(user_info: typing.Mapping) -> bool:
	"""
	Check if the superuser resource is present in the authorized resource list.
	"""
	return SUPERUSER_RES_ID in get_authorized_resources(user_info, tenant=None)


def has_resource_access(
	user_info: typing.Mapping,
	required_resources: typing.Iterable,
	tenant: typing.Union[str, None],
) -> bool:
	"""
	Check if the requested resources or the superuser resource are present in the authorized resource list.
	"""
	if has_superuser_access(user_info):
		return True

	authorized_resources = get_authorized_resources(user_info, tenant)
	for resource in required_resources:
		if resource not in authorized_resources:
			return False

	return True


def has_tenant_access(user_info: typing.Mapping, tenant: str) -> bool:
	"""
	Check if the request is authorized to access a tenant.
	If the request has superuser access, tenant access is always implicitly granted.
	"""
	if tenant == "*":
		raise ValueError("Invalid tenant name: '*'")
	if has_superuser_access(user_info):
		return True
	if tenant in user_info.get("resources", {}):
		return True
	return False


def get_authorized_resources(user_info: typing.Mapping, tenant: typing.Union[str, None]):
	return set(user_info.get("resources", {}).get(tenant if tenant is not None else "*", []))
