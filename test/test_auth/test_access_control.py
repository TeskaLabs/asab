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


class TestCommonUser(unittest.TestCase):
	Claims = {
		"resources": {
			"*": [
				RESOURCE_1,
			],
			TENANT_1: [
				RESOURCE_1,
				RESOURCE_2,
			],
		},
	}


	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
			),
			"RESOURCE_3 is not authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			"Both resources are authorized in TENANT_1.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Resource is authorized in TENANT_1.",
		)

		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			),
			"TENANT_2 is not authorized.",
		)

		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			),
			"TENANT_2 is not authorized.",
		)


	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			),
			"RESOURCE_2 is not authorized globally.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"RESOURCE_1 is authorized globally.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_1,
			),
			"TENANT_1 is authorized.",
		)

		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_2,
			),
			"TENANT_2 is not authorized.",
		)

		with self.assertRaises(ValueError):
			has_tenant_access(
				claims=self.Claims,
				tenant="*",
			)

		with self.assertRaises(ValueError):
			has_tenant_access(
				claims=self.Claims,
				tenant=None,
			)


	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				claims=self.Claims,
			),
			"Superuser resource is not authorized.",
		)


class TestTenantWithoutResources(unittest.TestCase):
	Claims = {
		"resources": {
			TENANT_1: [],
		},
	}


class TestSuperuser(unittest.TestCase):
	Claims = {
		"resources": {
			"*": [
				RESOURCE_SUPERUSER,
			],
		},
	}


	def test_tenant_resource_access(self):
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2, RESOURCE_3],
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			),
			"Superuser must have unrestricted resource access.",
		)


	def test_global_resource_access(self):
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			),
			"Superuser must have unrestricted resource access.",
		)

		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"Superuser must have unrestricted resource access.",
		)

		with self.assertRaises(ValueError):
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)


	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_1,
			),
			"Superuser must have unrestricted tenant access.",
		)

		with self.assertRaises(ValueError):
			has_tenant_access(
				claims=self.Claims,
				tenant="*",
			)

		with self.assertRaises(ValueError):
			has_tenant_access(
				claims=self.Claims,
				tenant=None,
			)


	def test_superuser(self):
		self.assertTrue(
			is_superuser(
				claims=self.Claims,
			),
			"Superuser resource must grant superuser privileges.",
		)


class TestEmptyClaims(unittest.TestCase):
	Claims = {}

	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"No authorized tenants or resources.",
		)

	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"No globally authorized resources.",
		)

	def test_tenant_access(self):
		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_2,
			),
			"No authorized tenants.",
		)

	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				claims=self.Claims,
			),
			"No authorized tenants or resources.",
		)


class TestEmptyResources(unittest.TestCase):
	Claims = {
		"resources": {},
	}

	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			),
			"No authorized tenants or resources.",
		)

	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			),
			"No globally authorized resources.",
		)

	def test_tenant_access(self):
		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_2,
			),
			"No authorized tenants.",
		)

	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				claims=self.Claims,
			),
			"No authorized tenants or resources.",
		)
