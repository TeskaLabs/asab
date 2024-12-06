import unittest

from asab.web.auth.authorization import (
	has_tenant_access,
	has_resource_access,
	is_superuser,
)
from .constants import (
	TENANT_1, TENANT_2,
	RESOURCE_1, RESOURCE_2, RESOURCE_3,
	RESOURCE_SUPERUSER,
)


class TestGlobalAndTenantResources(unittest.TestCase):
	"""
	This entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1, and RESOURCE_1 globally.

	Access check for RESOURCE_1 or RESOURCE_2 in TENANT_1 must return True.
	Global access check for RESOURCE_1 must return True.
	Any other access check for tenant or resource must return False.
	"""
	ResourcesClaim = {
		"*": [RESOURCE_1],
		TENANT_1: [RESOURCE_1, RESOURCE_2],
	}



	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
			),
			"Access to RESOURCE_3 is not authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			"Access to both resources is authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Access to RESOURCE_1 is authorized in TENANT_1.",
		)

		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			),
			"Access to RESOURCE_2 is not authorized globally.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"Access to RESOURCE_1 is authorized globally.",
		)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_1,
			),
			"Access to TENANT_1 is authorized.",
		)

		self.assertFalse(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"Access to superuser resource is not authorized.",
		)


class TestTenantWithoutResources(unittest.TestCase):
	"""
	This entity has authorized access to TENANT_1 but no resources.

	Only access check for TENANT_1 must return True.
	Access check for any resource or any other tenant must return False.
	"""

	ResourcesClaim = {
		TENANT_1: [],
	}


	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Access to RESOURCE_1 in TENANT_1 is not authorized.",
		)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"No resource is authorized globally.",
		)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_1,
			),
			"Access to TENANT_1 is authorized.",
		)

		self.assertFalse(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"Access to superuser resource is not authorized.",
		)


class TestTenantWithResources(unittest.TestCase):
	"""
	This entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1.

	Access check for RESOURCE_1 or RESOURCE_2 in TENANT_1 must return True.
	Any other access check for tenant or resource must return False.
	"""
	ResourcesClaim = {
		TENANT_1: [RESOURCE_1, RESOURCE_2],
	}

	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
			),
			"Access to RESOURCE_3 is not authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			"Access to both resources is authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Access to RESOURCE_1 is authorized in TENANT_1.",
		)

		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)

		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"No resource is authorized globally.",
		)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_1,
			),
			"Access to TENANT_1 is authorized.",
		)

		self.assertFalse(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_2,
			),
			"Access to TENANT_2 is not authorized.",
		)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"Access to superuser resource is not authorized.",
		)


class TestGlobalResourcesNoTenant(unittest.TestCase):
	"""
	This entity is globally authorized to access RESOURCE_1, but doesn't have access to any tenant.

	Only global access check for RESOURCE_1 must return True.
	Any other access check for tenant or resource must return False.
	"""
	ResourcesClaim = {
		"*": [RESOURCE_1],
	}


	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Access to TENANT_1 is not authorized.",
		)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			),
			"Access to RESOURCE_2 is not authorized globally.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"Access to RESOURCE_1 is authorized globally.",
		)


	def test_tenant_access(self):
		self.assertFalse(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_1,
			),
			"Access to TENANT_1 is not authorized.",
		)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"Access to superuser resource is not authorized.",
		)


class TestSuperuser(unittest.TestCase):
	"""
	This entity has authorized access to "authz:superuser" resource, which grants them
	superuser privileges.

	Access check for any tenant or resource must return True.
	Incorrect tenant values must still throw ValueError.
	"""

	ResourcesClaim = {
		"*": [RESOURCE_SUPERUSER],
	}


	def test_tenant_resource_access(self):
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			),
			"Superuser must have unrestricted resource access.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[],
				tenant=TENANT_1,
			)


	def test_global_resource_access(self):
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"Superuser must have unrestricted resource access.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant="*",
			)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted tenant access.",
		)

		with self.assertRaises(ValueError):
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant="*",
			)

		with self.assertRaises(ValueError):
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=None,
			)


	def test_superuser(self):
		self.assertTrue(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"Superuser resource must grant superuser privileges.",
		)


class TestEmptyResources(unittest.TestCase):
	ResourcesClaim = {}


	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"No authorized tenants or resources.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[],
				tenant=TENANT_1,
			)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"No globally authorized resources.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant="*",
			)


	def test_tenant_access(self):
		self.assertFalse(
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=TENANT_2,
			),
			"No authorized tenants.",
		)

		with self.assertRaises(ValueError):
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant="*",
			)

		with self.assertRaises(ValueError):
			has_tenant_access(
				resources_claim=self.ResourcesClaim,
				tenant=None,
			)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				resources_claim=self.ResourcesClaim,
			),
			"No authorized tenants or resources.",
		)
