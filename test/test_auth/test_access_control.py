import unittest

from asab.web.auth.authorization import (
	has_tenant_access,
	has_resource_access,
	is_superuser,
)


class TestAccessControlCommonUser(unittest.TestCase):
	Claims = {
		"resources": {
			"*": [
				"read",
			],
			"alpha-inc": [
				"read",
				"write",
			],
		},
	}

	def test_tenant_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write", "delete"],
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="alpha-inc",
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="beta-inc",
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="beta-inc",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="*",
			)
		)

	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant=None,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant=None,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="*",
			)
		)

	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant="alpha-inc",
			)
		)
		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant="beta-inc",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_tenant_access(
				claims=self.Claims,
				tenant="*",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_tenant_access(
				claims=self.Claims,
				tenant=None,
			)
		)

	def test_superuser(self):
		self.assertFalse(
			is_superuser(
				claims=self.Claims,
			)
		)


class TestAccessControlSuperuser(unittest.TestCase):
	Claims = {
		"resources": {
			"*": [
				"authz:superuser",
			],
		},
	}

	def test_tenant_resource_access(self):
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write", "delete"],
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="beta-inc",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="beta-inc",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="*",
			)
		)

	def test_global_resource_access(self):
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant=None,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant=None,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="*",
			)
		)

	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant="alpha-inc",
			)
		)
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant="beta-inc",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_tenant_access(
				claims=self.Claims,
				tenant="*",
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_tenant_access(
				claims=self.Claims,
				tenant=None,
			)
		)

	def test_superuser(self):
		self.assertTrue(
			is_superuser(
				claims=self.Claims,
			)
		)
