import datetime
import typing
import logging

from ...exceptions import AccessDeniedError
from ...contextvars import Tenant

L = logging.getLogger(__name__)


SUPERUSER_RESOURCE_ID = "authz:superuser"


class Authorization:
	"""
	Contains authentication and authorization details, provides methods for checking access control
	"""
	def __init__(self, auth_service, userinfo: dict):
		self.AuthService = auth_service
		if self.AuthService.is_enabled() and userinfo is None:
			L.error("Userinfo is mandatory when AuthService is enabled.")
			raise AccessDeniedError()
		self.UserInfo = userinfo or {}

		self.CredentialsId = self.UserInfo.get("sub")
		self.Username = self.UserInfo.get("preferred_username") or self.UserInfo.get("username")
		self.Email = self.UserInfo.get("email")
		self.Phone = self.UserInfo.get("phone")

		self.Expiration = datetime.datetime.fromtimestamp(int(self.UserInfo.get("exp")), datetime.timezone.utc)
		self.Issuer = self.UserInfo.get("iss")  # Who issued the authorization
		self.AuthorizedParty = self.UserInfo.get("azp")  # What party (application) is authorized


	def __repr__(self):
		return "<Authorization [{}cid: {!r}, azp: {!r}]>".format(
			"SUPERUSER, " if self.is_superuser() else "",
			self.CredentialsId,
			self.AuthorizedParty,
		)


	def is_valid(self) -> bool:
		"""
		Check if the authorization is not expired.
		:return: Authorization validity
		"""
		return datetime.datetime.now(datetime.timezone.utc) > self.Expiration


	def is_superuser(self) -> bool:
		"""
		Check whether the agent is a superuser.

		:return: Is the agent a superuser?
		"""
		if not self.AuthService.is_enabled():
			# Authorization is disabled = everything is allowed
			return True

		if not self.is_valid():
			return False

		return is_superuser(self.UserInfo)


	def has_resource_access(self, *resources: typing.Iterable[str]) -> bool:
		"""
		Check whether the agent is authorized to access requested resources.

		:param resources: List of resource IDs whose authorization is requested.
		:return: Is resource access authorized?
		"""
		if not self.AuthService.is_enabled():
			# Authorization is disabled = everything is allowed
			return True

		if not self.is_valid():
			return False

		return has_resource_access(self.UserInfo, resources, tenant=Tenant.get(None))


	def require_superuser(self):
		"""
		Assert that the agent has superuser access.
		"""
		if not self.is_superuser():
			raise AccessDeniedError()


	def require_resource_access(self, *resources: typing.Iterable[str]):
		"""
		Assert that the agent is authorized to access the required resources.
		:param resources: List of resource IDs whose authorization is required.
		"""
		if not self.has_resource_access(*resources):
			raise AccessDeniedError()


	def authorized_resources(self) -> typing.Optional[typing.Set[str]]:
		"""
		Return the set of EXPLICITLY authorized resources. (Use carefully with superusers.)

		NOTE: If possible, use methods has_resource_access(resource_id) and is_superuser() instead of inspecting
		the set of resources.

		:return: Set of authorized resources.
		"""
		if not self.AuthService.is_enabled():
			# Authorization is disabled = authorized resources are undefined
			return None

		if not self.is_valid():
			return None

		return get_authorized_resources(self.UserInfo, Tenant.get(None))


def is_superuser(userinfo: typing.Mapping) -> bool:
	"""
	Check if the superuser resource is present in the authorized resource list.
	"""
	return SUPERUSER_RESOURCE_ID in get_authorized_resources(userinfo, tenant=None)


def has_resource_access(
	userinfo: typing.Mapping,
	resources: typing.Iterable,
	tenant: typing.Union[str, None],
) -> bool:
	"""
	Check if the requested resources or the superuser resource are present in the authorized resource list.
	"""
	if is_superuser(userinfo):
		return True

	authorized_resources = get_authorized_resources(userinfo, tenant)
	for resource in resources:
		if resource not in authorized_resources:
			return False

	return True


def has_tenant_access(userinfo: typing.Mapping, tenant: str) -> bool:
	"""
	Check the agent's userinfo to see if they are authorized to access a tenant.
	If the agent has superuser access, tenant access is always implicitly granted.
	"""
	if tenant == "*":
		raise ValueError("Invalid tenant name: '*'")
	if is_superuser(userinfo):
		return True
	if tenant in userinfo.get("resources", {}):
		return True
	return False


def get_authorized_resources(userinfo: typing.Mapping, tenant: typing.Union[str, None]) -> typing.Set[str]:
	"""
	Extract resources authorized within given tenant (or globally, if tenant is None).

	:param userinfo:
	:param tenant:
	:return: Set of authorized resources.
	"""
	return set(userinfo.get("resources", {}).get(tenant if tenant is not None else "*", []))
