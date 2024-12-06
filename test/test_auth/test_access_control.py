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


class TestAccessControlCommonUser(unittest.TestCase):
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
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			)
		)
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)
		)

	def test_global_resource_access(self):
		self.assertFalse(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)
		)

	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_1,
			)
		)
		self.assertFalse(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_2,
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
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_1,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_1,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=TENANT_2,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=TENANT_2,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)
		)

	def test_global_resource_access(self):
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1, RESOURCE_2],
				tenant=None,
			)
		)
		self.assertTrue(
			has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant=None,
			)
		)
		self.assertRaises(
			ValueError,
			lambda: has_resource_access(
				claims=self.Claims,
				resources=[RESOURCE_1],
				tenant="*",
			)
		)

	def test_tenant_access(self):
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_1,
			)
		)
		self.assertTrue(
			has_tenant_access(
				claims=self.Claims,
				tenant=TENANT_2,
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
