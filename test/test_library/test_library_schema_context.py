"""
Context and repeatability tests for LibrarySchemaService.

These tests cover repeated reads and caller mutation isolation.
"""

import tempfile
import unittest

from test.test_library.library_schema_test_utils import make_filesystem_provider, make_schema_service, write_fixture


class TestLibrarySchemaContext(unittest.IsolatedAsyncioTestCase):

	async def test_read_schema_returns_same_result_across_calls(self):
		"""Repeated reads of unchanged schema files return the same effective schema."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Custom.yaml", "extension_custom_foo.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			first_schema = await service.read_schema("/Schemas/ECS.yaml")
			second_schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(first_schema, second_schema)

	async def test_result_mutation_does_not_change_stored_schema(self):
		"""Mutating a returned schema does not affect future read_schema results."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Custom.yaml", "extension_custom_foo.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			first_schema = await service.read_schema("/Schemas/ECS.yaml")
			first_schema["fields"]["host.name"]["type"] = "changed"
			first_schema["fields"]["custom.foo"]["type"] = "changed"
			second_schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(second_schema["fields"]["host.name"]["type"], "str")
			self.assertEqual(second_schema["fields"]["custom.foo"]["type"], "str")
