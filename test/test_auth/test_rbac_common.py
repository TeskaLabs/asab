import unittest

from asab.web.auth.authorization import (
	has_tenant_access,
	has_resource_access,
	is_superuser,
)


class TestCommonUser(unittest.TestCase):
	Claims = {
		"resources": {
			"*": [
				"read",
			],
			"good": [
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
				tenant="good",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="good",
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="good",
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read", "write"],
				tenant="bad",
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=["read"],
				tenant="bad",
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
				tenant="good",
			)
		)
		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant="bad",
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
