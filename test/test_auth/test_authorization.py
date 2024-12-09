import unittest
import time

import asab.contextvars
import asab.exceptions
from asab.web.auth.authorization import Authorization

TENANT_1 = "TENANT_1"
TENANT_2 = "TENANT_2"
RESOURCE_1 = "RESOURCE_1"
RESOURCE_2 = "RESOURCE_2"
RESOURCE_3 = "RESOURCE_3"
RESOURCE_SUPERUSER = "authz:superuser"


class TestInvalidClaims(unittest.TestCase):
	"""
	Entity is missing mandatory authorization claims.

	Authorization object should not initialize.
	"""

	def setUp(self):
		super().setUp()
		self.TenantCtx = asab.contextvars.Tenant.set(TENANT_1)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)

	def test_missing_expiration(self):
		claims = {
			"iat": time.time() - 60,
		}
		with self.assertRaises(KeyError):
			Authorization(claims)

	def test_missing_issued_at(self):
		claims = {
			"exp": time.time() + 3600,
		}
		with self.assertRaises(KeyError):
			Authorization(claims)


class TestExpiredSuperuser(unittest.TestCase):
	"""
	Entity has expired superuser authorization.

	All access control methods must raise asab.exceptions.NotAuthenticatedError.
	"""
	def setUp(self):
		super().setUp()
		claims = {
			"iat": time.time() - 60,
			"exp": time.time() - 10,  # Expired 10 seconds ago
			"resources": {
				"*": [RESOURCE_SUPERUSER],
				TENANT_1: [RESOURCE_SUPERUSER, RESOURCE_1],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(TENANT_1)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertFalse(
			self.Authz.is_valid(),
			"Expired authorization must return False.",
		)

		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.require_valid()

	def test_resource_access(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.has_resource_access(RESOURCE_1)

		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.require_resource_access(RESOURCE_1)

	def test_tenant_access(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.has_tenant_access()

		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.require_tenant_access()

	def test_superuser_access(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.has_superuser_access()

		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.require_superuser_access()

	def test_authorized_resources(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz._resources()

	def test_get_claim(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.get_claim("anything")

	def test_user_info(self):
		with self.assertRaises(asab.exceptions.NotAuthenticatedError):
			self.Authz.user_info()


class TestTenantAuthorized(unittest.TestCase):
	"""
	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.
	It is accessing TENANT_1 (in context).
	"""
	def setUp(self):
		super().setUp()

		claims = {
			"iat": time.time() - 60,
			"exp": time.time() + 3600,
			"resources": {
				"*": [RESOURCE_1],
				TENANT_1: [RESOURCE_1, RESOURCE_2],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(TENANT_1)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertTrue(
			self.Authz.is_valid(),
			"Unexpired authorization must return True.",
		)

		self.assertIsNone(
			self.Authz.require_valid(),
			"Unexpired authorization must succeed without return."
		)

	def test_resource_access(self):
		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1),
			"Access to RESOURCE_1 is authorized.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1),
			"Authorized access to RESOURCE_1 must succeed without return.",
		)

		self.assertFalse(
			self.Authz.has_resource_access(RESOURCE_1, RESOURCE_3),
			"Access to RESOURCE_3 is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_resource_access(RESOURCE_1, RESOURCE_3)

	def test_tenant_access(self):
		self.assertTrue(
			self.Authz.has_tenant_access(),
			"Access to TENANT_1 is authorized.",
		)

		self.assertIsNone(
			self.Authz.require_tenant_access(),
			"Authorized access to TENANT_1 must succeed without return.",
		)

	def test_superuser_access(self):
		self.assertFalse(
			self.Authz.has_superuser_access(),
			"Access to superuser resource is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_superuser_access()

	def test_authorized_resources(self):
		self.assertEqual(
			self.Authz._resources(),
			{RESOURCE_1, RESOURCE_2},
			"Entity is authorized to access RESOURCE_1, RESOURCE_2 in TENANT_1.",
		)


class TestTenantForbidden(unittest.TestCase):
	"""
	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.
	It is accessing TENANT_1 (in context).

	All has-access methods must return False.
	All require-access methods must raise asab.exceptions.AccessDeniedError.
	"""
	def setUp(self):
		super().setUp()

		claims = {
			"iat": time.time() - 60,
			"exp": time.time() + 3600,
			"resources": {
				"*": [RESOURCE_1],
				TENANT_1: [RESOURCE_1, RESOURCE_2],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(TENANT_2)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertTrue(
			self.Authz.is_valid(),
			"Unexpired authorization must return True.",
		)

		self.assertIsNone(
			self.Authz.require_valid(),
			"Unexpired authorization must succeed without return."
		)

	def test_resource_access(self):
		self.assertFalse(
			self.Authz.has_resource_access(RESOURCE_1),
			"Access to RESOURCE_1 is not authorized in TENANT_2.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_resource_access(RESOURCE_1)

	def test_tenant_access(self):
		self.assertFalse(
			self.Authz.has_tenant_access(),
			"Access to TENANT_2 is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_tenant_access()

	def test_superuser_access(self):
		self.assertFalse(
			self.Authz.has_superuser_access(),
			"Access to superuser resource is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_superuser_access()

	def test_authorized_resources(self):
		self.assertEqual(
			self.Authz._resources(),
			set(),
			"Entity is authorized to access RESOURCE_1, RESOURCE_2 in TENANT_1.",
		)


class TestGlobal(unittest.TestCase):
	"""
	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.
	It is accessing global space - Tenant context is empty.

	All has-access methods must return True.
	All require-access methods must return None.
	"""
	def setUp(self):
		super().setUp()

		claims = {
			"iat": time.time() - 60,
			"exp": time.time() + 3600,
			"resources": {
				"*": [RESOURCE_1],
				TENANT_1: [RESOURCE_1, RESOURCE_2],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(None)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertTrue(
			self.Authz.is_valid(),
			"Unexpired authorization must return True.",
		)

		self.assertIsNone(
			self.Authz.require_valid(),
			"Unexpired authorization must succeed without return."
		)

	def test_resource_access(self):
		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1),
			"Global access to RESOURCE_1 is authorized.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1),
			"Authorized global access to RESOURCE_1 must succeed without return.",
		)

		self.assertFalse(
			self.Authz.has_resource_access(RESOURCE_1, RESOURCE_2),
			"Global access to RESOURCE_2 is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_resource_access(RESOURCE_1, RESOURCE_2)

	def test_tenant_access(self):
		# There is no tenant in the context, hence ValueError
		with self.assertRaises(ValueError):
			self.Authz.has_tenant_access()

		with self.assertRaises(ValueError):
			self.Authz.require_tenant_access()

	def test_superuser_access(self):
		self.assertFalse(
			self.Authz.has_superuser_access(),
			"Access to superuser resource is not authorized.",
		)

		with self.assertRaises(asab.exceptions.AccessDeniedError):
			self.Authz.require_superuser_access()

	def test_authorized_resources(self):
		self.assertEqual(
			self.Authz._resources(),
			{RESOURCE_1},
			"Entity is globally authorized to access RESOURCE_1.",
		)


class TestSuperuserTenant(unittest.TestCase):
	"""
	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.
	It is accessing TENANT_1 (in context).
	"""
	def setUp(self):
		super().setUp()

		claims = {
			"iat": time.time() - 60,
			"exp": time.time() + 3600,
			"resources": {
				"*": [RESOURCE_SUPERUSER],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(TENANT_1)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertTrue(
			self.Authz.is_valid(),
			"Unexpired authorization must return True.",
		)

		self.assertIsNone(
			self.Authz.require_valid(),
			"Unexpired authorization must succeed without return."
		)

	def test_resource_access(self):
		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1),
			"Superuser must have unrestricted resource access.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1),
			"Authorized superuser access to any resource must succeed without return.",
		)

		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1, RESOURCE_3),
			"Superuser must have unrestricted resource access.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1, RESOURCE_3),
			"Authorized superuser access to any resource must succeed without return.",
		)

	def test_tenant_access(self):
		self.assertTrue(
			self.Authz.has_tenant_access(),
			"Superuser must have unrestricted tenant access.",
		)

		self.assertIsNone(
			self.Authz.require_tenant_access(),
			"Authorized superuser access to any tenant must succeed without return.",
		)

	def test_superuser_access(self):
		self.assertTrue(
			self.Authz.has_superuser_access(),
			"Superuser must have unrestricted tenant access.",
		)

		self.assertIsNone(
			self.Authz.require_superuser_access(),
			"Authorized superuser access must succeed without return.",
		)

	def test_authorized_resources(self):
		self.assertEqual(
			self.Authz._resources(),
			{RESOURCE_SUPERUSER},
		)


class TestSuperuserGlobal(unittest.TestCase):
	"""
	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.
	It is accessing global space - Tenant context is empty.

	All has-access methods must return True.
	All require-access methods must return None.
	"""
	def setUp(self):
		super().setUp()

		claims = {
			"iat": time.time() - 60,
			"exp": time.time() + 3600,
			"resources": {
				"*": [RESOURCE_SUPERUSER],
			},
		}
		self.Authz = Authorization(claims)
		self.TenantCtx = asab.contextvars.Tenant.set(None)

	def tearDown(self):
		super().tearDown()
		asab.contextvars.Tenant.reset(self.TenantCtx)
		self.Authz = None

	def test_valid(self):
		self.assertTrue(
			self.Authz.is_valid(),
			"Unexpired authorization must return True.",
		)

		self.assertIsNone(
			self.Authz.require_valid(),
			"Unexpired authorization must succeed without return."
		)

	def test_resource_access(self):
		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1),
			"Superuser must have unrestricted resource access.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1),
			"Authorized superuser access to any resource must succeed without return.",
		)

		self.assertTrue(
			self.Authz.has_resource_access(RESOURCE_1, RESOURCE_3),
			"Superuser must have unrestricted resource access.",
		)

		self.assertIsNone(
			self.Authz.require_resource_access(RESOURCE_1, RESOURCE_3),
			"Authorized superuser access to any resource must succeed without return.",
		)

	def test_tenant_access(self):
		# There is no tenant in the context, hence ValueError
		with self.assertRaises(ValueError):
			self.Authz.has_tenant_access()

		with self.assertRaises(ValueError):
			self.Authz.require_tenant_access()

	def test_superuser_access(self):
		self.assertTrue(
			self.Authz.has_superuser_access(),
			"Superuser must have unrestricted tenant access.",
		)

		self.assertIsNone(
			self.Authz.require_superuser_access(),
			"Authorized superuser access must succeed without return.",
		)

	def test_authorized_resources(self):
		self.assertEqual(
			self.Authz._resources(),
			{RESOURCE_SUPERUSER},
		)