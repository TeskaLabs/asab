import asyncio
import os
from pathlib import Path

from asab.library.item import LibraryItem
from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.library.schema import LibrarySchemaService
from asab.library.service import LibraryService


SCHEMA_DATA_ROOT = Path(__file__).with_name("library_schema")


def write_fixture(root, path, fixture_name):
	full_path = os.path.join(root, path.lstrip("/"))
	os.makedirs(os.path.dirname(full_path), exist_ok=True)
	with open(full_path, "w", encoding="utf-8") as f:
		f.write((SCHEMA_DATA_ROOT / fixture_name).read_text(encoding="utf-8"))


def make_filesystem_provider(root):
	provider = FileSystemLibraryProvider.__new__(FileSystemLibraryProvider)
	provider.BasePath = root
	provider.Layer = 0
	provider.IsReady = True
	return provider


class VanishingExtensionProvider(FileSystemLibraryProvider):

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


def make_vanishing_extension_provider(root):
	provider = VanishingExtensionProvider.__new__(VanishingExtensionProvider)
	provider.BasePath = root
	provider.Layer = 0
	provider.IsReady = True
	return provider


def make_schema_service(provider):
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
