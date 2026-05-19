import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library_schema_test_utils import (
	make_filesystem_provider,
	make_schema_service,
	make_vanishing_extension_provider,
	write_extension,
	write_fixture,
)


DUPLICATE_FIELD_WARNING = "Skipping field: Field found in base schema or other schema extension."


class TestLibrarySchemaExtensions(unittest.IsolatedAsyncioTestCase):

	async def test_extension_adds_new_field(self):
		"""A matching .yaml extension contributes a new field."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"custom.foo": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.foo"]["type"], "str")

	async def test_malformed_extension_is_skipped(self):
		"""A malformed extension is skipped while later valid extensions still merge."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Bad.yaml", "malformed.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Good.yaml", {"custom.good": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")

	async def test_extension_without_fields_mapping_is_skipped(self):
		"""An extension without a fields mapping is skipped without blocking valid ones."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Bad.yaml", "extension_no_fields.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Good.yaml", {"custom.good": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")
			self.assertTrue(
				any("'fields' section is not a dictionary" in message for message in logs.output),
				"Extension without fields mapping should log why it was skipped.",
			)

	async def test_non_mapping_extension_is_skipped(self):
		"""An extension YAML document that is not a mapping is skipped."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_fixture(root, "/Schemas/Extensions/ECS-Bad.yaml", "document_list.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Good.yaml", {"custom.good": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")
			self.assertTrue(
				any("File is not a dictionary" in message for message in logs.output),
				"Non-mapping extension should log why it was skipped.",
			)

	async def test_unreadable_extension_candidate_is_skipped(self):
		"""A listed extension that cannot be opened is skipped while valid extensions merge."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Good.yaml", {"custom.good": "str"})
			service = make_schema_service(make_vanishing_extension_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")
			self.assertNotIn("custom.vanished", schema["fields"])

	async def test_extension_field_does_not_overwrite_base_field(self):
		"""An extension cannot overwrite an existing base field."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"host.name": "keyword"})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["host.name"]["type"],
				"str",
				"Extension must not overwrite the base host.name field.",
			)
			self.assertTrue(
				any(DUPLICATE_FIELD_WARNING in message for message in logs.output),
				"Duplicate extension field should log that it was skipped.",
			)

	async def test_extension_with_multiple_conflicts_only_adds_non_conflicting_fields(self):
		"""Conflicting extension fields are skipped, but safe fields from the same file merge."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Conflict.yaml", {
				"host.name": "keyword",
				"event.created": "str",
				"custom.safe": "bool",
			})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["host.name"]["type"],
				"str",
				"Conflicting extension field host.name must keep the base definition.",
			)
			self.assertEqual(
				schema["fields"]["event.created"]["type"],
				"datetime",
				"Conflicting extension field event.created must keep the base definition.",
			)
			self.assertEqual(
				schema["fields"]["custom.safe"]["type"],
				"bool",
				"Non-conflicting field from the same extension should still be merged.",
			)
			self.assertEqual(
				sum(DUPLICATE_FIELD_WARNING in message for message in logs.output),
				2,
				"Both conflicting extension fields should log duplicate skips.",
			)

	async def test_extension_for_other_schema_is_ignored(self):
		"""Extensions for a different schema name are ignored."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/CEF-Custom.yaml", {"cef.only": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("cef.only", schema["fields"])

	async def test_requested_schema_uses_only_matching_extension_prefix(self):
		"""Reading CFM picks only CFM-* extensions, not ECS-* or CFMX-*."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/CFM.yaml", "base_cfm.yaml")
			write_extension(root, "/Schemas/Extensions/CFM-Custom.yaml", {"cfm.only": "str"})
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"ecs.only": "str"})
			write_extension(root, "/Schemas/Extensions/CFMX-Custom.yaml", {"cfmx.only": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("CFM")

			self.assertIn("flow.id", schema["fields"], "CFM base schema field should be present.")
			self.assertIn("cfm.only", schema["fields"], "CFM-* extension should be merged for CFM schema reads.")
			self.assertNotIn("ecs.only", schema["fields"], "ECS-* extension must not be merged into CFM schema reads.")
			self.assertNotIn("cfmx.only", schema["fields"], "CFMX-* extension must not match the CFM-* prefix.")

	async def test_non_yaml_extension_file_is_ignored(self):
		"""Matching schema extension candidates must use a YAML file extension."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Custom.json", {"custom.json": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("custom.json", schema["fields"])

	async def test_empty_extension_name_is_ignored(self):
		"""The extension naming convention requires a non-empty suffix after schema-."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-.yaml", {"custom.empty": "str"})
			write_extension(root, "/Schemas/Extensions/ECS-Custom.yaml", {"custom.good": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("custom.empty", schema["fields"])
			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")

	async def test_duplicate_extension_fields_are_resolved_by_filename_sort_order(self):
		"""Extension merge order is deterministic even when files are created out of order."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-Z-last.yaml", {"custom.order": "keyword"})
			write_extension(root, "/Schemas/Extensions/ECS-A-first.yaml", {"custom.order": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["custom.order"]["type"],
				"str",
				"First extension by sorted filename should win duplicate field conflicts.",
			)
			self.assertTrue(
				any(DUPLICATE_FIELD_WARNING in message for message in logs.output),
				"Later duplicate field should log that it was skipped.",
			)

	async def test_duplicate_extension_keeps_first_field_and_merges_later_unique_fields(self):
		"""A later duplicate extension can still contribute fields that do not conflict."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			write_extension(root, "/Schemas/Extensions/ECS-A.yaml", {"custom.shared": "str"})
			write_extension(root, "/Schemas/Extensions/ECS-B.yaml", {
				"custom.shared": "keyword",
				"custom.unique": "long",
			})
			service = make_schema_service(make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["custom.shared"]["type"],
				"str",
				"Later duplicate extension field should not overwrite the first definition.",
			)
			self.assertEqual(
				schema["fields"]["custom.unique"]["type"],
				"long",
				"Later extension should still merge fields that do not conflict.",
			)
			self.assertTrue(
				any(DUPLICATE_FIELD_WARNING in message for message in logs.output),
				"Later duplicate field should log that it was skipped.",
			)

	async def test_extension_directory_is_not_read(self):
		"""Directory entries that look like extension files are ignored before reading."""
		with tempfile.TemporaryDirectory() as root:
			write_fixture(root, "/Schemas/ECS.yaml", "base_ecs.yaml")
			os.makedirs(os.path.join(root, "Schemas", "Extensions", "ECS-Directory.yaml"))
			write_extension(root, "/Schemas/Extensions/ECS-Good.yaml", {"custom.good": "str"})
			service = make_schema_service(make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")
