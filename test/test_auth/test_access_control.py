import unittest

from asab.web.auth.authorization import (
	has_tenant_access,
	has_resource_access,
	is_superuser,
)

TENANT_1 = "TENANT_1"
TENANT_2 = "TENANT_2"
RESOURCE_1 = "RESOURCE_1"
RESOURCE_2 = "RESOURCE_2"
RESOURCE_3 = "RESOURCE_3"
RESOURCE_SUPERUSER = "authz:superuser"


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


class TestResourceMatchAny(unittest.TestCase):
	"""
	Test the 'match' parameter for 'any' matching mode.

	Entity is authorized to access RESOURCE_1 in TENANT_1.
	With match="any", access check should pass if at least one resource is authorized.
	"""
	ResourcesClaim = {
		TENANT_1: [RESOURCE_1],
	}

	def test_match_any_one_resource(self):
		# Single authorized resource should pass
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
				match="any",
			),
			"Access to RESOURCE_1 is authorized (single resource).",
		)

	def test_match_any_multiple_authorized(self):
		# Multiple resources, one is authorized - should pass with match="any"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
				match="any",
			),
			"Access to at least one resource is authorized with match='any'.",
		)

	def test_match_any_none_authorized(self):
		# None of the resources authorized - should fail even with match="any"
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
				match="any",
			),
			"None of the resources are authorized even with match='any'.",
		)

	def test_match_any_unauthorized_tenant(self):
		# Unauthorized tenant - should fail regardless of match
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
				match="any",
			),
			"Access to TENANT_2 is not authorized even with match='any'.",
		)


class TestResourceMatchAll(unittest.TestCase):
	"""
	Test the 'match' parameter for 'all' matching mode (default behavior).

	Entity is authorized to access RESOURCE_1 and RESOURCE_2 in TENANT_1.
	With match="all", access check should pass only if all resources are authorized.
	"""
	ResourcesClaim = {
		TENANT_1: [RESOURCE_1, RESOURCE_2],
	}

	def test_match_all_all_authorized(self):
		# All resources authorized - should pass with match="all"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
				match="all",
			),
			"All resources are authorized with match='all'.",
		)

	def test_match_all_one_unauthorized(self):
		# Not all resources authorized - should fail with match="all"
		self.assertFalse(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_3],
				tenant=TENANT_1,
				match="all",
			),
			"RESOURCE_3 is not authorized, should fail with match='all'.",
		)

	def test_match_all_single_authorized(self):
		# Single authorized resource should pass with match="all"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
				match="all",
			),
			"Single authorized resource passes with match='all'.",
		)

	def test_match_all_default(self):
		# Default behavior (no match parameter) should be same as match="all"
		self.assertEqual(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
				match="all",
			),
			"Default behavior should match match='all'.",
		)


class TestResourceMatchInvalid(unittest.TestCase):
	"""
	Test the 'match' parameter with invalid values.
	"""
	ResourcesClaim = {
		TENANT_1: [RESOURCE_1],
	}

	def test_match_invalid_value(self):
		with self.assertRaises(ValueError) as context:
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
				match="invalid",
			)
		self.assertIn("match must be either 'all' or 'any'", str(context.exception))


class TestResourceMatchAnySuperuser(unittest.TestCase):
	"""
	Test the 'match' parameter with superuser authorization.

	Superuser should have unrestricted access regardless of match mode.
	"""
	ResourcesClaim = {
		"*": [RESOURCE_SUPERUSER],
	}

	def test_superuser_match_any_unrestricted(self):
		# Superuser should have access to any resources with match="any"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
				match="any",
			),
			"Superuser must have unrestricted resource access with match='any'.",
		)

	def test_superuser_match_all_unrestricted(self):
		# Superuser should have access to all resources with match="all"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
				match="all",
			),
			"Superuser must have unrestricted resource access with match='all'.",
		)

	def test_superuser_match_any_unauthorized_tenant(self):
		# Superuser should have access even to unauthorized tenants with match="any"
		self.assertTrue(
			has_resource_access(
				resources_claim=self.ResourcesClaim,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
				match="any",
			),
			"Superuser must have unrestricted tenant access with match='any'.",
		)
