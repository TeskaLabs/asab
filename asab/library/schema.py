import copy
import logging
import os.path

import yaml

from ..abc import Service
from ..exceptions import LibraryError, LibraryInvalidPathError
from .item import LibraryItem
from .service import _validate_path_item


L = logging.getLogger(__name__)


class LibrarySchemaService(Service):
	"""
	Read and merge global library schemas from an explicitly configured service.

	This service is intentionally separate from `LibraryService`: applications that
	only need generic library reads/lists/subscriptions do not need to instantiate
	or depend on schema-specific behavior.
	"""

	def __init__(self, app, service_name: str, library_service):
		super().__init__(app, service_name)
		self.LibraryService = library_service

	async def read_schema(
		self,
		schema_path: str,
	):
		"""
		Build the effective LMIO schema for `schema_path`.

		The effective schema is computed from one authoritative base schema and zero
		or more extension schemas:

		`/Schemas/<schema>.yaml`
		`/Schemas/Extensions/<schema>-*.yaml`

		This is not a generic YAML merge. It is a deterministic, additive merge of
		the top-level `fields` mapping. The base schema is left-biased: existing
		fields are never overwritten, so extensions can only contribute fields that
		do not already exist in the accumulated result.

		The base schema path must be provided explicitly as `/Schemas/<schema>.yaml`.
		"""
		await self.LibraryService.wait_for_library_ready()
		schema_path, schema_name, extensions_path = _schema_path(schema_path)

		try:
			async with self.LibraryService.open(schema_path) as itemio:
				if itemio is None:
					base_schema = None
				else:
					base_schema = yaml.load(itemio, Loader=yaml.CSafeLoader)
		except Exception as e:
			raise LibraryError(
				"Failed to parse schema '{}': {}".format(schema_path, e)
			) from e

		if base_schema is None:
			raise LibraryError("Schema '{}' not found.".format(schema_path))

		self._validate_base_schema(schema_path, base_schema)
		merged_schema = copy.deepcopy(base_schema)
		merged_fields = merged_schema["fields"]
		try:
			extension_items = await self.LibraryService.list(extensions_path)
		except KeyError:
			extension_items = []

		extension_items = sorted(
			(
				item for item in extension_items
				if _is_schema_extension_item(item, schema_name)
			),
			key=lambda item: item.name,
		)

		for item in extension_items:
			if item.disabled:
				continue
			try:
				async with self.LibraryService.open(item.name) as itemio:
					if itemio is None:
						extension = None
					else:
						extension = yaml.load(itemio, Loader=yaml.CSafeLoader)
			except Exception as e:
				L.warning(
					"Skipping schema extension: Failed to read or parse YAML.",
					struct_data={
						"path": item.name,
						"error": str(e),
					},
				)
				continue

			if extension is None:
				continue

			if not isinstance(extension, dict):
				L.warning(
					"Skipping schema extension: File is not a dictionary.",
					struct_data={
						"path": item.name,
					},
				)
				continue
			if not _has_schema_type(extension, "lmio/schema-extension"):
				L.warning(
					"Skipping schema extension: Invalid define/type.",
					struct_data={
						"path": item.name,
					},
				)
				continue
			extension_fields = extension.get("fields")
			if not isinstance(extension_fields, dict):
				L.warning(
					"Skipping schema extension: 'fields' section is not a dictionary.",
					struct_data={
						"path": item.name,
					},
				)
				continue

			for field_name, field_definition in extension_fields.items():
				if field_name in merged_fields:
					L.warning(
						"Skipping schema extension field: field already exists.",
						struct_data={
							"path": item.name,
							"field": field_name,
						},
					)
					continue
				merged_fields[field_name] = copy.deepcopy(field_definition)

		return merged_schema

	def _validate_base_schema(self, path: str, schema: dict) -> None:
		"""
		Validate the minimum structure needed before additive merging.

		The base schema is the fixed point of the merge: all returned schemas must
		preserve its fields exactly. For this first iteration we only require the
		shape needed by the merge algorithm: a YAML mapping with a top-level
		`fields` mapping.
		"""
		if not isinstance(schema, dict):
			raise LibraryError("Schema '{}' must be a YAML mapping.".format(path))

		if not _has_schema_type(schema, "lmio/schema"):
			raise LibraryError("Schema '{}' must have define/type 'lmio/schema'.".format(path))

		fields = schema.get("fields")
		if not isinstance(fields, dict):
			raise LibraryError("Schema '{}' must contain a 'fields' mapping.".format(path))


def _schema_path(schema: str) -> tuple[str, str, str]:
	"""
	Validate a `/Schemas/<name>.yaml` path and derive schema locations.

	Returns `(schema_path, schema_name, extensions_path)`. For example,
	`"/Schemas/ECS.yaml"` becomes `("/Schemas/ECS.yaml", "ECS",
	"/Schemas/Extensions/")`.
	"""
	if not isinstance(schema, str) or schema == "":
		raise LibraryInvalidPathError(
			message="Schema path must be a non-empty string.",
			path=str(schema),
		)

	if not schema.startswith("/Schemas/"):
		raise LibraryInvalidPathError(
			message="Schema path must be under '/Schemas/'.",
			path=schema,
		)
	path = schema

	_validate_path_item(path)

	directory, filename = os.path.split(path)
	if directory != "/Schemas":
		raise LibraryInvalidPathError(
			message="Schema path must be under '/Schemas/'.",
			path=path,
		)

	schema_name, extension = os.path.splitext(filename)
	if extension != ".yaml":
		raise LibraryInvalidPathError(
			message="Schema path must use the '.yaml' extension.",
			path=path,
		)
	extensions_path = "{}/Extensions/".format(directory.rstrip("/"))
	return path, schema_name, extensions_path


def _has_schema_type(schema: dict, expected_type: str) -> bool:
	define = schema.get("define")
	if not isinstance(define, dict):
		return False
	return define.get("type") == expected_type


def _is_schema_extension_item(item: LibraryItem, schema_name: str) -> bool:
	"""
	Return `True` when a listed library item is a leaf extension candidate.

	Extension files use the `<schema-name>-<extension-name>.yaml` naming
	convention. Directory entries and non-YAML files are ignored before any read is
	attempted.
	"""
	if item.type != "item":
		return False

	filename = os.path.basename(item.name)
	name, extension = os.path.splitext(filename)
	if extension != ".yaml":
		return False

	prefix = "{}-".format(schema_name)
	return name.startswith(prefix) and len(name) > len(prefix)
