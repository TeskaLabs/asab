import typing


class Authorization:
	"""
	Contains authentication and authorization details, provides methods for checking access control
	"""
	def __init__(self, auth_service, userinfo: dict, tenant: typing.Optional[str] = None):
		self.AuthService = auth_service
		self.Userinfo = userinfo
		self.CredentialsId = userinfo.get("sub")
		self.Username = userinfo.get("preferred_username") or userinfo.get("username")
		self.Email = userinfo.get("email")
		self.Phone = userinfo.get("phone")

		self.Tenant = tenant

	def has_superuser_access(self):
		return self.AuthService.has_superuser_access(self.Userinfo)

	def has_resource_access(self, resource_id: str | typing.Iterable[str]):
		if isinstance(resource_id, str):
			return self.AuthService.has_resource_access(self.Userinfo, self.Tenant, {resource_id})
		else:
			return self.AuthService.has_resource_access(self.Userinfo, self.Tenant, resource_id)
