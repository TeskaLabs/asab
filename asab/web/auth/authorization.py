import datetime
import typing
import logging

from ...exceptions import AccessDeniedError, NotAuthenticatedError
from ...contextvars import Tenant

L = logging.getLogger(__name__)


SUPERUSER_RESOURCE_ID = "authz:superuser"


class Authorization:
	"""
	Contains authentication and authorization claims, provides methods for checking and enforcing access control.

	Attributes:
		CredentialsId (str):
			Unique identifier of the authorized entity in the ASAB ecosystem.
			Usually corresponds to JWT attribute "sub".
		Username (str): End-user's preferred username.
		Email (str): End-user email address.
		Phone (str): End-user phone number.
		SessionId (str): Sign-on session identifier.
		Issuer (str): Unique identifier of the server that issued the authorization.
		IssuedAt (datetime.datetime): Timestamp when the authorization was issued.
		Expiration (datetime.datetime): Timestamp when the authorization expires.
	"""
	def __init__(self, claims: dict):
		"""
		Initialize Authorization object from authorization server claims.

		Args:
			claims (dict): Authorization server claims (from ID token, UserInfo etc.).
		"""
		# Userinfo should not be accessed directly
		self._Claims = claims or {}
		self._Resources = self._Claims.get("resources", {})

		self.CredentialsId = self._Claims.get("sub")
		self.Username = self._Claims.get("preferred_username") or self._Claims.get("username")
		self.Email = self._Claims.get("email")
		self.Phone = self._Claims.get("phone")
		self.SessionId = self._Claims.get("sid")

		self.Issuer = self._Claims.get("iss")  # Who issued the authorization
		self.IssuedAt = datetime.datetime.fromtimestamp(int(self._Claims["iat"]), datetime.timezone.utc)
		self.Expiration = datetime.datetime.fromtimestamp(int(self._Claims["exp"]), datetime.timezone.utc)


	def __repr__(self):
		return "<Authorization [{}cid: {!r}, iat: {!r}, exp: {!r}]>".format(
			"SUPERUSER, " if self.has_superuser_access() else "",
			self.CredentialsId,
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
		return is_superuser(self._Resources)


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
		return has_resource_access(self._Resources, resources, tenant=Tenant.get(None))


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
			>>>     	print("I have access to Big Corporation!")
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

		return has_tenant_access(self._Resources, tenant)


	def require_valid(self):
		"""
		Ensure that the authorization is not expired.
		"""
		if not self.is_valid():
			L.warning("Authorization expired.", struct_data={
				"cid": self.CredentialsId, "exp": self.Expiration.isoformat()})
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
				"cid": self.CredentialsId})
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
				"resource": resources, "cid": self.CredentialsId})
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
				"tenant": Tenant.get(), "cid": self.CredentialsId})
			raise AccessDeniedError()


	def user_info(self) -> typing.Dict[str, typing.Any]:
		"""
		Return OpenID Connect UserInfo claims (or JWToken claims).

		NOTE: If possible, use Authz attributes (CredentialsId, Username etc.) instead of inspecting
		the claims directly.

		Returns:
			dict: UserInfo claims
		"""
		self.require_valid()
		return self._Claims


	def get_claim(self, key: str) -> typing.Any:
		"""
		Get the value of a token claim.

		Args:
			key: Claim name.

		Returns:
			Value of the requested claim (or `None` if the claim is not present).
		"""
		self.require_valid()
		return self._Claims.get(key)


	def _resources(self) -> typing.Optional[typing.Set[str]]:
		"""
		Return the set of authorized resources.

		Returns:
			set: Authorized resources.
		"""
		self.require_valid()

		resources = _authorized_resources(self._Resources, Tenant.get(None))

		if self.has_superuser_access():
			# Ensure superuser resource is present no matter the tenant
			resources.add(SUPERUSER_RESOURCE_ID)

		return resources


def is_superuser(resources_claim: typing.Mapping) -> bool:
	"""
	Check if the superuser resource is present in the authorized resource list.

	Args:
		resources_claim (typing.Mapping): The "resources" field from authorization server claims (aka UserInfo).

	Returns:
		bool: Do I have superuser access?
	"""
	return SUPERUSER_RESOURCE_ID in _authorized_resources(resources_claim, tenant=None)


def has_resource_access(
	resources_claim: typing.Mapping,
	resources: typing.Collection[str],
	tenant: typing.Union[str, None],
) -> bool:
	"""
	Check if the requested resources or the superuser resource are present in the authorized resource list.

	Args:
		resources_claim (typing.Mapping): The "resources" field from authorization server claims (aka UserInfo).
		resources (typing.Collection[str]): A list of resource IDs whose authorization is requested.
		tenant (str): Tenant context of the authorization (or `None` for global context).

	Returns:
		bool: Am I authorized to access requested resources?
	"""
	if len(resources) == 0:
		raise ValueError("Resources must not be empty")

	authorized_resources = _authorized_resources(resources_claim, tenant)

	if is_superuser(resources_claim):
		return True

	for resource in resources:
		if resource not in authorized_resources:
			return False

	return True


def has_tenant_access(resources_claim: typing.Mapping, tenant: str) -> bool:
	"""
	Check the agent's userinfo to see if they are authorized to access a tenant.
	If the agent has superuser access, tenant access is always implicitly granted.

	Args:
		resources_claim (typing.Mapping): The "resources" field from authorization server claims (aka UserInfo).
		tenant (str): Tenant context of the authorization.

	Returns:
		bool: Am I authorized to access requested tenant?
	"""
	if tenant in {"*", None}:
		raise ValueError("Invalid tenant: {!r}".format(tenant))

	if is_superuser(resources_claim):
		return True

	if tenant in resources_claim:
		return True

	return False


def _authorized_resources(resources_claim: typing.Mapping, tenant: typing.Union[str, None]) -> typing.Set[str]:
	"""
	Extract resources authorized within given tenant (or globally, if tenant is None).

	Args:
		resources_claim (typing.Mapping): The "resources" field from authorization server claims (aka UserInfo).
		tenant (str): Tenant context of the authorization (or `None` for global context).

	Returns:
		set: Resources authorized within the tenant (or globally).
	"""
	if tenant == "*":
		# Use `None` for global context instead!
		raise ValueError("Invalid tenant name: {}".format(tenant))

	return set(resources_claim.get(tenant if tenant is not None else "*", []))
