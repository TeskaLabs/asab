"""
Validation tests for LibrarySchemaService.

These tests cover base schema presence, base schema structure, and schema path
constraints for `/Schemas/<name>.yaml`.
"""

import tempfile
import unittest

from asab.exceptions import LibraryError, LibraryInvalidPathError
from test.test_library.library_schema_test_utils import make_filesystem_provider, make_schema_service, write_fixture


class TestLibrarySchemaValidation(unittest.IsolatedAsyncioTestCase):

	async def test_missing_base_schema_raises_library_error(self):
		"""A missing base schema fails the schema read."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("/Schemas/ECS.yaml")

	async def test_malformed_base_schema_raises_library_error(self):
		"""A base schema with the wrong YAML shape fails the whole schema read."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "document_list.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("/Schemas/ECS.yaml")

	async def test_base_schema_without_fields_mapping_raises_library_error(self):
		"""A base schema must provide a top-level fields mapping."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_no_fields.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("/Schemas/ECS.yaml")

	async def test_base_schema_without_lmio_schema_type_raises_library_error(self):
		"""A base schema must identify itself as an LMIO schema."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_wrong_type.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("/Schemas/ECS.yaml")

	async def test_short_schema_name_is_rejected(self):
		"""Schemas must be requested by full /Schemas/<name>.yaml path."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("ECS")

	async def test_relative_schema_path_is_rejected(self):
		"""Relative schema paths are rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("../ECS")

	async def test_empty_schema_path_is_rejected(self):
		"""An empty schema path is rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("")

	async def test_non_string_schema_path_is_rejected(self):
		"""A non-string schema path is rejected before any provider access."""
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

			schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(set(schema["fields"]), {"host.name", "event.created"})

	async def test_absolute_schema_path_uses_matching_extension_prefix(self):
		"""An absolute schema path still derives the correct extension prefix."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Custom.yaml", "extension_custom_foo.yaml")
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(schema["fields"]["custom.foo"]["type"], "str")
