import datetime
import typing
import logging

from ...exceptions import AccessDeniedError, NotAuthenticatedError
from ...contextvars import Tenant

L = logging.getLogger(__name__)


SUPERUSER_RESOURCE_ID = "authz:superuser"


class Authorization:
	"""
	Contains authentication and authorization details, provides methods for checking and enforcing access control.

	Requires that AuthService is initialized and enabled.
	"""
	def __init__(self, auth_service, userinfo: dict):
		self.AuthService = auth_service
		if not self.AuthService.is_enabled():
			raise ValueError("Cannot create Authorization when AuthService is disabled.")

		# Userinfo should not be accessed directly
		self._UserInfo = userinfo or {}

		self.CredentialsId = self._UserInfo.get("sub")
		self.Username = self._UserInfo.get("preferred_username") or self._UserInfo.get("username")
		self.Email = self._UserInfo.get("email")
		self.Phone = self._UserInfo.get("phone")

		self.Issuer = self._UserInfo.get("iss")  # Who issued the authorization
		self.AuthorizedParty = self._UserInfo.get("azp")  # What party (application) is authorized
		self.IssuedAt = datetime.datetime.fromtimestamp(int(self._UserInfo["iat"]), datetime.timezone.utc)
		self.Expiration = datetime.datetime.fromtimestamp(int(self._UserInfo["exp"]), datetime.timezone.utc)


	def __repr__(self):
		return "<Authorization [{}cid: {!r}, azp: {!r}, iat: {!r}, exp: {!r}]>".format(
			"SUPERUSER, " if self.has_superuser_access() else "",
			self.CredentialsId,
			self.AuthorizedParty,
			self.IssuedAt.isoformat(),
			self.Expiration.isoformat(),
		)


	def is_valid(self):
		"""
		Check that the authorization is not expired.
		"""
		return datetime.datetime.now(datetime.timezone.utc) < self.Expiration


	def has_superuser_access(self) -> bool:
		"""
		Check whether the agent is a superuser.

		Returns:
			bool: Do I have superuser access?

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> if authz.has_superuser_access():
			>>>     print("I am a superuser and can do anything!")
			>>> else:
			>>>     print("I am but a mere mortal.")
		"""
		self.require_valid()
		return is_superuser(self._UserInfo)


	def has_resource_access(self, *resources: str) -> bool:
		"""
		Check whether the agent is authorized to access requested resources.

		Args:
			*resources (str): A variable number of resource IDs whose authorization is requested.

		Returns:
			bool: Am I authorized to access requested resources?

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> if authz.has_resource_access("article:read", "article:write"):
			>>>     print("I can read and write articles!")
			>>> else:
			>>>     print("Not much to do here.")
		"""
		self.require_valid()
		return has_resource_access(self._UserInfo, resources, tenant=Tenant.get(None))


	def has_tenant_access(self) -> bool:
		"""
		Check whether the agent has access to the tenant in context.

		Returns:
			bool: Am I authorized to access requested tenant?

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> tenant_ctx = asab.contextvars.Tenant.set("big-corporation")
			>>> try:
			>>>     if authz.has_tenant_access():
			>>>         print("I have access to Big Corporation!")
			>>>     else:
			>>>         print("Not much to do here.")
			>>> finally:
			>>>     asab.contextvars.Tenant.reset(tenant_ctx)
		"""
		self.require_valid()

		try:
			tenant = Tenant.get()
		except LookupError as e:
			raise ValueError("No tenant in context.") from e

		return has_tenant_access(self._UserInfo, tenant)


	def require_valid(self):
		"""
		Ensure that the authorization is not expired.
		"""
		if not self.is_valid():
			L.warning("Authorization expired.", struct_data={
				"cid": self.CredentialsId, "azp": self.AuthorizedParty, "exp": self.Expiration.isoformat()})
			raise NotAuthenticatedError()


	def require_superuser_access(self):
		"""
		Ensure that the agent has superuser access.

        Raises:
            AccessDeniedError: If I do not have superuser access.

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> authz.require_superuser_access()
			>>> print("I am a superuser and can do anything!")
		"""
		if not self.has_superuser_access():
			L.warning("Superuser authorization required.", struct_data={
				"cid": self.CredentialsId, "azp": self.AuthorizedParty})
			raise AccessDeniedError()


	def require_resource_access(self, *resources: str):
		"""
		Ensure that the agent is authorized to access the specified resources.

		Args:
			*resources (str): A variable number of resource IDs whose authorization is requested.

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> authz.require_resource_access("article:read", "article:write")
			>>> print("I can read and write articles!")
		"""
		if not self.has_resource_access(*resources):
			L.warning("Resource authorization required.", struct_data={
				"resource": resources, "cid": self.CredentialsId, "azp": self.AuthorizedParty})
			raise AccessDeniedError()


	def require_tenant_access(self):
		"""
		Ensures that the agent is authorized to access the tenant in the current context.

        Raises:
            AccessDeniedError: If the agent does not have access to the tenant.

		Examples:
			>>> import asab.contextvars
			>>> authz = asab.contextvars.Authz.get()
			>>> tenant_ctx = asab.contextvars.Tenant.set("big-corporation")
			>>> try:
			>>>     authz.require_tenant_access()
			>>>     print("I have access to Big Corporation!")
			>>> finally:
			>>>     asab.contextvars.Tenant.reset(tenant_ctx)
		"""
		if not self.has_tenant_access():
			L.warning("Tenant authorization required.", struct_data={
				"tenant": Tenant.get(), "cid": self.CredentialsId, "azp": self.AuthorizedParty})
			raise AccessDeniedError()


	def authorized_resources(self) -> typing.Optional[typing.Set[str]]:
		"""
		Return the set of authorized resources.

		NOTE: If possible, use methods has_resource_access(resource_id) and has_superuser_access() instead of inspecting
		the set of resources directly.

		Returns:
			Set of authorized resources.
		"""
		self.require_valid()
		return get_authorized_resources(self._UserInfo, Tenant.get(None))


	def user_info(self) -> typing.Dict[str, typing.Any]:
		"""
		Return OpenID Connect UserInfo.

		NOTE: If possible, use Authz attributes (CredentialsId, Username etc.) instead of inspecting the user info
		dictionary directly.

		Returns:
		 	User info
		"""
		self.require_valid()
		return self._UserInfo


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
