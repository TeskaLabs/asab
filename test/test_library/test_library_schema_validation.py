"""
Validation tests for LibrarySchemaService.

These tests cover base schema presence, base schema structure, schema-name
validation, and absolute path constraints for `/Schemas/<name>.yaml`.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from asab.exceptions import LibraryError, LibraryInvalidPathError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library_schema_test_utils import make_filesystem_provider, make_schema_service, write_extension, write_fixture


class TestLibrarySchemaValidation(unittest.IsolatedAsyncioTestCase):

	async def test_missing_base_schema_raises_library_error(self):
		"""A missing base schema fails the schema read."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("ECS")

	async def test_malformed_base_schema_raises_library_error(self):
		"""A base schema with the wrong YAML shape fails the whole schema read."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "document_list.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("ECS")

	async def test_base_schema_without_fields_mapping_raises_library_error(self):
		"""A base schema must provide a top-level fields mapping."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_no_fields.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("ECS")

	async def test_invalid_schema_name_is_rejected(self):
		"""Relative schema paths are rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("../ECS")

	async def test_empty_schema_name_is_rejected(self):
		"""An empty schema name is rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("")

	async def test_non_string_schema_name_is_rejected(self):
		"""A non-string schema identifier is rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema(None)

	async def test_absolute_schema_path_outside_schemas_is_rejected(self):
		"""An absolute schema path must stay under /Schemas/."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("/CustomSchemas/CFM.yaml")

	async def test_nested_absolute_schema_path_is_rejected(self):
		"""An absolute schema path must be a direct /Schemas/<name>.yaml file."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("/Schemas/Extensions/CFM.yaml")

	async def test_base_schema_only_returns_base_schema(self):
		"""When no extensions exist, the effective schema contains only base fields."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(set(schema["fields"]), {"host.name", "event.created"})

	async def test_absolute_schema_path_uses_matching_extension_prefix(self):
		"""An absolute schema path still derives the correct extension prefix."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"custom.foo": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(schema["fields"]["custom.foo"]["type"], "str")
