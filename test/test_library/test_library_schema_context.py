"""
Context and repeatability tests for LibrarySchemaService.

These tests cover repeated reads, caller mutation isolation, and global-only
schema resolution when tenant context is set.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import asab.contextvars

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library_schema_test_utils import make_filesystem_provider, make_schema_service, write_extension, write_schema, write_fixture


class TestLibrarySchemaContext(unittest.IsolatedAsyncioTestCase):

	async def test_read_schema_returns_same_result_across_calls(self):
		"""Repeated reads of unchanged schema files return the same effective schema."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"custom.foo": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			first_schema = await service.read_schema("ECS")
			second_schema = await service.read_schema("ECS")

			self.assertEqual(first_schema, second_schema)

	async def test_result_mutation_does_not_change_stored_schema(self):
		"""Mutating a returned schema does not affect future read_schema results."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"custom.foo": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			first_schema = await service.read_schema("ECS")
			first_schema["fields"]["host.name"]["type"] = "changed"
			first_schema["fields"]["custom.foo"]["type"] = "changed"
			second_schema = await service.read_schema("ECS")

			self.assertEqual(second_schema["fields"]["host.name"]["type"], "str")
			self.assertEqual(second_schema["fields"]["custom.foo"]["type"], "str")

	async def test_schema_reads_ignore_tenant_overlays(self):
		"""Schema reads force global resolution and ignore tenant overlay files."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Global.yaml", {"global.field": "str"})
			write_schema(root, "/.tenants/acme/Schemas/ECS.yaml", {"tenant.base": "str"})
			write_extension(root, "/.tenants/acme/Schemas/Extensions/ECS-Tenant.yaml", {"tenant.field": "str"})
			service = make_schema_service(make_filesystem_provider(root))
			tenant_ctx = asab.contextvars.Tenant.set("acme")

			try:
				schema = await service.read_schema("ECS")
			finally:
				asab.contextvars.Tenant.reset(tenant_ctx)

			self.assertIn(
				"host.name",
				schema["fields"],
				"Global base schema field should be present even with tenant context set.",
			)
			self.assertIn(
				"global.field",
				schema["fields"],
				"Global schema extension should be merged even with tenant context set.",
			)
			self.assertNotIn(
				"tenant.base",
				schema["fields"],
				"Tenant overlay base schema must be ignored by schema reads.",
			)
			self.assertNotIn(
				"tenant.field",
				schema["fields"],
				"Tenant overlay schema extension must be ignored by schema reads.",
			)
