import contextlib
import copy
import logging
import os.path

import yaml

from ..abc import Service
from ..contextvars import Authz, Tenant
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
		schema: str = "ECS",
		timeout: int = None,
	):
		"""
		Build the effective global LMIO schema for `schema`.

		The effective schema is computed from one authoritative base schema and zero
		or more extension schemas:

		`/Schemas/<schema>.yaml`
		`/Schemas/Extensions/<schema>-*.yaml`

		This is not a generic YAML merge. It is a deterministic, additive merge of
		the top-level `fields` mapping. The base schema is left-biased: existing
		fields are never overwritten, so extensions can only contribute fields that
		do not already exist in the accumulated result.

		Schema reads intentionally ignore tenant and personal overlays. Schemas are
		global contracts, so base and extension files are resolved from the global
		library layer even when tenant context variables are set.
		"""
		await self.LibraryService.wait_for_library_ready(timeout)
		schema_path, schema_name, extensions_path = _schema_path(schema)

		with self._global_library_context():
			try:
				base_schema = await self._read_schema_yaml(schema_path)
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
					extension = await self._read_schema_yaml(item.name)
				except Exception:
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
							"Skipping field: Field found in base schema or other schema extension.",
							struct_data={
								"path": item.name,
								"field": field_name,
							},
						)
						continue
					merged_fields[field_name] = copy.deepcopy(field_definition)

			return merged_schema

	@contextlib.contextmanager
	def _global_library_context(self):
		"""
		Temporarily clear tenant/auth context variables for global-only schema reads.

		Provider `read()` and `list()` implementations normally honor tenant and
		personal overlays. Schemas are intentionally global contracts, so
		`read_schema()` uses this context manager to force global resolution while
		restoring the caller's context afterward.
		"""
		tenant_ctx = Tenant.set(None)
		authz_ctx = Authz.set(None)
		try:
			yield
		finally:
			Authz.reset(authz_ctx)
			Tenant.reset(tenant_ctx)

	async def _read_schema_yaml(self, path: str):
		"""
		Read and parse a schema-related YAML library item.

		Returns `None` when the item does not exist or is disabled.
		Parsed YAML values, including `None` from empty/null YAML files, are
		returned as-is so schema validation can report the real problem. YAML
		parser errors are intentionally propagated to the caller so `read_schema()`
		can decide whether to fail the base schema read or skip an extension.

		This helper intentionally relies on `open()` and is expected to run inside
		`_global_library_context()` so schema reads resolve against the global layer.
		"""
		async with self.LibraryService.open(path) as itemio:
			if itemio is None:
				return None
			return yaml.load(itemio, Loader=yaml.CSafeLoader)

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

		fields = schema.get("fields")
		if not isinstance(fields, dict):
			raise LibraryError("Schema '{}' must contain a 'fields' mapping.".format(path))


def _schema_path(schema: str) -> tuple[str, str, str]:
	"""
	Normalize a schema name or `/Schemas/<name>.yaml` path into schema locations.

	Returns `(schema_path, schema_name, extensions_path)`. For example, `"ECS"`
	becomes `("/Schemas/ECS.yaml", "ECS", "/Schemas/Extensions/")`.
	"""
	if not isinstance(schema, str) or schema == "":
		raise LibraryInvalidPathError(
			message="Schema name must be a non-empty string.",
			path=str(schema),
		)

	if schema.startswith("/"):
		path = schema
	elif "/" in schema or "\\" in schema or schema in (".", ".."):
		raise LibraryInvalidPathError(
			message="Schema name must not contain path separators.",
			path=schema,
		)
	else:
		path = "/Schemas/{}.yaml".format(schema)

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
