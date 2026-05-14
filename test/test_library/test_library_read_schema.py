"""
read_schema() unit test intent:

- Missing, malformed, and structurally invalid base schemas are handled explicitly.
- Invalid schema names and paths are rejected before provider reads.
- Empty and non-string schema inputs are rejected.
- Absolute schema paths outside `/Schemas/<name>.yaml` are rejected.
- A valid base schema is returned unchanged when no extensions are available.
- Valid `.yaml` extensions add only new fields to the effective schema.
- Malformed, non-mapping, non-YAML, directory, empty-name, and wrong-schema
  extension candidates are ignored.
- The requested schema name selects only matching `<schema>-*.yaml` extension files.
- Conflict cases are left-biased: base fields beat extension fields, and the first
  sorted extension beats later duplicate extension fields.
- The merge is deterministic across calls and returned data is isolated from caller
  mutation.
- Schema reads force global context and ignore tenant overlays.
"""

import asyncio
import os
import tempfile
import unittest

import asab.contextvars
from asab.exceptions import LibraryError, LibraryInvalidPathError
from asab.library.item import LibraryItem
from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.library.schema import LibrarySchemaService
from asab.library.service import LibraryService


def _yaml(lines):
	return "\n".join(lines) + "\n"


BASE_SCHEMA = _yaml([
	"---",
	"define:",
	"  name: Elastic Common Schema",
	"  type: lmio/schema",
	"fields:",
	"  host.name:",
	"    type: str",
	"  event.created:",
	"    type: datetime",
])


def _extension_schema(field_name: str, field_type: str) -> str:
	return _yaml([
		"---",
		"define:",
		"  type: lmio/schema-extension",
		"fields:",
		"  {}:".format(field_name),
		"    type: {}".format(field_type),
	])


def _write(root, path, content):
	full_path = os.path.join(root, path.lstrip("/"))
	os.makedirs(os.path.dirname(full_path), exist_ok=True)
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(content)


def _make_filesystem_provider(root):
	provider = FileSystemLibraryProvider.__new__(FileSystemLibraryProvider)
	provider.BasePath = root
	provider.Layer = 0
	provider.IsReady = True
	return provider


class _VanishingExtensionProvider(FileSystemLibraryProvider):

	async def list(self, path):
		items = await super().list(path)
		if path == "/Schemas/Extensions/":
			items.append(LibraryItem(
				name="/Schemas/Extensions/ECS-Vanished.yaml",
				type="item",
				layers=[self.Layer],
				providers=[self],
			))
		return items


def _make_vanishing_extension_provider(root):
	provider = _VanishingExtensionProvider.__new__(_VanishingExtensionProvider)
	provider.BasePath = root
	provider.Layer = 0
	provider.IsReady = True
	return provider


def _make_service(provider):
	library_service = LibraryService.__new__(LibraryService)
	library_service.Libraries = [provider]
	library_service.Disabled = {}
	library_service.DisabledPaths = []
	library_service.Favorites = {}
	library_service.FavoritePaths = []
	library_service.LibraryReadyEvent = asyncio.Event()
	library_service.LibraryReadyEvent.set()
	library_service.LibraryReadyTimeout = 0.01

	schema_service = LibrarySchemaService.__new__(LibrarySchemaService)
	schema_service.LibraryService = library_service
	return schema_service


class TestLibraryReadSchema(unittest.IsolatedAsyncioTestCase):

	async def test_missing_base_schema_returns_none(self):
		"""A missing base schema is treated as absent and returns None."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertIsNone(schema)

	async def test_malformed_base_schema_raises_library_error(self):
		"""A base schema with the wrong YAML shape fails the whole schema read."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", "[]")
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("ECS")

	async def test_base_schema_without_fields_mapping_raises_library_error(self):
		"""A base schema must provide a top-level fields mapping."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema",
			]))
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryError):
				await service.read_schema("ECS")

	async def test_invalid_schema_name_is_rejected(self):
		"""Relative schema paths are rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("../ECS")

	async def test_empty_schema_name_is_rejected(self):
		"""An empty schema name is rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("")

	async def test_non_string_schema_name_is_rejected(self):
		"""A non-string schema identifier is rejected before any provider access."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema(None)

	async def test_absolute_schema_path_outside_schemas_is_rejected(self):
		"""An absolute schema path must stay under /Schemas/."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("/CustomSchemas/CFM.yaml")

	async def test_nested_absolute_schema_path_is_rejected(self):
		"""An absolute schema path must be a direct /Schemas/<name>.yaml file."""
		with tempfile.TemporaryDirectory() as root:
			service = _make_service(_make_filesystem_provider(root))

			with self.assertRaises(LibraryInvalidPathError):
				await service.read_schema("/Schemas/Extensions/CFM.yaml")

	async def test_base_schema_only_returns_base_schema(self):
		"""When no extensions exist, the effective schema contains only base fields."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(set(schema["fields"]), {"host.name", "event.created"})

	async def test_extension_adds_new_field(self):
		"""A matching .yaml extension contributes a new field."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("custom.foo", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.foo"]["type"], "str")

	async def test_malformed_extension_is_skipped(self):
		"""A malformed extension is skipped while later valid extensions still merge."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Bad.yaml", "fields: [")
			_write(root, "/Schemas/Extensions/ECS-Good.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")

	async def test_extension_without_fields_mapping_is_skipped(self):
		"""An extension without a fields mapping is skipped without blocking valid ones."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Bad.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema-extension",
			]))
			_write(root, "/Schemas/Extensions/ECS-Good.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_filesystem_provider(root))

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
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Bad.yaml", "[]")
			_write(root, "/Schemas/Extensions/ECS-Good.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_filesystem_provider(root))

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
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Good.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_vanishing_extension_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")
			self.assertNotIn("custom.vanished", schema["fields"])

	async def test_extension_field_does_not_overwrite_base_field(self):
		"""An extension cannot overwrite an existing base field."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("host.name", "keyword"))
			service = _make_service(_make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["host.name"]["type"],
				"str",
				"Extension must not overwrite the base host.name field.",
			)
			self.assertTrue(
				any("Skipping field: Duplicate." in message for message in logs.output),
				"Duplicate extension field should log that it was skipped.",
			)

	async def test_extension_with_multiple_conflicts_only_adds_non_conflicting_fields(self):
		"""Conflicting extension fields are skipped, but safe fields from the same file merge."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Conflict.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema-extension",
				"fields:",
				"  host.name:",
				"    type: keyword",
				"  event.created:",
				"    type: str",
				"  custom.safe:",
				"    type: bool",
			]))
			service = _make_service(_make_filesystem_provider(root))

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
				sum("Skipping field: Duplicate." in message for message in logs.output),
				2,
				"Both conflicting extension fields should log duplicate skips.",
			)

	async def test_extension_for_other_schema_is_ignored(self):
		"""Extensions for a different schema name are ignored."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/CEF-Custom.yaml", _extension_schema("cef.only", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("cef.only", schema["fields"])

	async def test_requested_schema_uses_only_matching_extension_prefix(self):
		"""Reading CFM picks only CFM-* extensions, not ECS-* or CFMX-*."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/CFM.yaml", _yaml([
				"---",
				"define:",
				"  name: Custom Flow Model",
				"  type: lmio/schema",
				"fields:",
				"  flow.id:",
				"    type: str",
			]))
			_write(root, "/Schemas/Extensions/CFM-Custom.yaml", _extension_schema("cfm.only", "str"))
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("ecs.only", "str"))
			_write(root, "/Schemas/Extensions/CFMX-Custom.yaml", _extension_schema("cfmx.only", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("CFM")

			self.assertIn(
				"flow.id",
				schema["fields"],
				"CFM base schema field should be present.",
			)
			self.assertIn(
				"cfm.only",
				schema["fields"],
				"CFM-* extension should be merged for CFM schema reads.",
			)
			self.assertNotIn(
				"ecs.only",
				schema["fields"],
				"ECS-* extension must not be merged into CFM schema reads.",
			)
			self.assertNotIn(
				"cfmx.only",
				schema["fields"],
				"CFMX-* extension must not match the CFM-* prefix.",
			)

	async def test_non_yaml_extension_file_is_ignored(self):
		"""Matching schema extension candidates must use a YAML file extension."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.json", _extension_schema("custom.json", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("custom.json", schema["fields"])

	async def test_empty_extension_name_is_ignored(self):
		"""The extension naming convention requires a non-empty suffix after schema-."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-.yaml", _extension_schema("custom.empty", "str"))
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertNotIn("custom.empty", schema["fields"])
			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")

	async def test_duplicate_extension_fields_are_resolved_by_filename_sort_order(self):
		"""Extension merge order is deterministic even when files are created out of order."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Z-last.yaml", _extension_schema("custom.order", "keyword"))
			_write(root, "/Schemas/Extensions/ECS-A-first.yaml", _extension_schema("custom.order", "str"))
			service = _make_service(_make_filesystem_provider(root))

			with self.assertLogs("asab.library.schema", level="WARNING") as logs:
				schema = await service.read_schema("ECS")

			self.assertEqual(
				schema["fields"]["custom.order"]["type"],
				"str",
				"First extension by sorted filename should win duplicate field conflicts.",
			)
			self.assertTrue(
				any("Skipping field: Duplicate." in message for message in logs.output),
				"Later duplicate field should log that it was skipped.",
			)

	async def test_duplicate_extension_keeps_first_field_and_merges_later_unique_fields(self):
		"""A later duplicate extension can still contribute fields that do not conflict."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-A.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema-extension",
				"fields:",
				"  custom.shared:",
				"    type: str",
			]))
			_write(root, "/Schemas/Extensions/ECS-B.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema-extension",
				"fields:",
				"  custom.shared:",
				"    type: keyword",
				"  custom.unique:",
				"    type: long",
			]))
			service = _make_service(_make_filesystem_provider(root))

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
				any("Skipping field: Duplicate." in message for message in logs.output),
				"Later duplicate field should log that it was skipped.",
			)

	async def test_read_schema_returns_same_result_across_calls(self):
		"""Repeated reads of unchanged schema files return the same effective schema."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("custom.foo", "str"))
			service = _make_service(_make_filesystem_provider(root))

			first_schema = await service.read_schema("ECS")
			second_schema = await service.read_schema("ECS")

			self.assertEqual(first_schema, second_schema)

	async def test_result_mutation_does_not_change_stored_schema(self):
		"""Mutating a returned schema does not affect future read_schema results."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("custom.foo", "str"))
			service = _make_service(_make_filesystem_provider(root))

			first_schema = await service.read_schema("ECS")
			first_schema["fields"]["host.name"]["type"] = "changed"
			first_schema["fields"]["custom.foo"]["type"] = "changed"
			second_schema = await service.read_schema("ECS")

			self.assertEqual(second_schema["fields"]["host.name"]["type"], "str")
			self.assertEqual(second_schema["fields"]["custom.foo"]["type"], "str")

	async def test_absolute_schema_path_uses_matching_extension_prefix(self):
		"""An absolute schema path still derives the correct extension prefix."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Custom.yaml", _extension_schema("custom.foo", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("/Schemas/ECS.yaml")

			self.assertEqual(schema["fields"]["custom.foo"]["type"], "str")

	async def test_schema_reads_ignore_tenant_overlays(self):
		"""Schema reads force global resolution and ignore tenant overlay files."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			_write(root, "/Schemas/Extensions/ECS-Global.yaml", _extension_schema("global.field", "str"))
			_write(root, "/.tenants/acme/Schemas/ECS.yaml", _yaml([
				"---",
				"define:",
				"  type: lmio/schema",
				"fields:",
				"  tenant.base:",
				"    type: str",
			]))
			_write(root, "/.tenants/acme/Schemas/Extensions/ECS-Tenant.yaml", _extension_schema("tenant.field", "str"))
			service = _make_service(_make_filesystem_provider(root))
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

	async def test_extension_directory_is_not_read(self):
		"""Directory entries that look like extension files are ignored before reading."""
		with tempfile.TemporaryDirectory() as root:
			_write(root, "/Schemas/ECS.yaml", BASE_SCHEMA)
			os.makedirs(os.path.join(root, "Schemas", "Extensions", "ECS-Directory.yaml"))
			_write(root, "/Schemas/Extensions/ECS-Good.yaml", _extension_schema("custom.good", "str"))
			service = _make_service(_make_filesystem_provider(root))

			schema = await service.read_schema("ECS")

			self.assertEqual(schema["fields"]["custom.good"]["type"], "str")


if __name__ == "__main__":
	unittest.main()
