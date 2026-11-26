"""Symmetry tests for FileSystemLibraryProvider target roots."""

import logging
import os
import tempfile
import unittest
from types import SimpleNamespace

import asab
import asab.abc

from asab.contextvars import Authz, Tenant
from asab.library.providers.filesystem import FileSystemLibraryProvider


class _Library(object):
	def __init__(self, app):
		self.App = app

	async def _set_ready(self, provider):
		pass

	async def _read_disabled(self, publish_changes=False):
		pass


def _write_file(root, library_path, content):
	full_path = os.path.join(root, library_path.lstrip("/"))
	os.makedirs(os.path.dirname(full_path), exist_ok=True)
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(content)


class TestFileSystemLibraryProviderTargets(unittest.IsolatedAsyncioTestCase):

	async def asyncSetUp(self):
		self.tmpdir = tempfile.TemporaryDirectory()
		self.root = self.tmpdir.name
		_write_file(self.root, "/Templates/item.json", "global-item")
		_write_file(self.root, "/.tenants/acme/Templates/item.json", "tenant-item")
		_write_file(self.root, "/.personal/acme/user1/Templates/item.json", "personal-item")
		_write_file(self.root, "/.tenants/acme/OverlayOnly/tenant.json", "tenant-only")
		_write_file(self.root, "/.personal/acme/user1/OverlayOnly/personal.json", "personal-only")

		self.App = asab.Application(args=[], modules=[])
		self.provider = FileSystemLibraryProvider(
			_Library(self.App),
			self.root,
			0,
			source=self.root,
			enable_inotify=False,
		)

	async def asyncTearDown(self):
		await self.provider.finalize(self.App)
		asab.abc.singleton.Singleton.delete(self.App.__class__)
		self.App = None
		self.tmpdir.cleanup()
		logging.getLogger().handlers = []

	def test_target_bases_differ_only_by_prefix(self):
		self.assertEqual(self.provider._target_base("global"), self.root)
		self.assertEqual(
			self.provider._target_base("tenant", tenant_id="acme"),
			os.path.join(self.root, ".tenants", "acme"),
		)
		self.assertEqual(
			self.provider._target_base("personal", tenant_id="acme", cred_id="user1"),
			os.path.join(self.root, ".personal", "acme", "user1"),
		)

	def test_tenant_without_context_does_not_alias_global(self):
		self.assertIsNone(self.provider.build_path("/Templates/", "tenant"))
		self.assertEqual(
			self.provider.build_path("/Templates/item.json", "global"),
			os.path.join(self.root, "Templates", "item.json"),
		)

	def test_personal_without_credentials_is_skipped(self):
		tenant_token = Tenant.set("acme")
		try:
			self.assertIsNone(self.provider.build_path("/Templates/", "personal"))
		finally:
			Tenant.reset(tenant_token)

	def test_path_traversal_rejected_for_all_targets(self):
		for target, kwargs in (
			("global", {}),
			("tenant", {"tenant_id": "acme"}),
			("personal", {"tenant_id": "acme", "cred_id": "user1"}),
		):
			with self.assertRaises(ValueError):
				self.provider.build_path("/../outside.json", target, **kwargs)

	async def test_read_walks_targets_in_same_way(self):
		stream = await self.provider.read("/Templates/item.json")
		self.assertEqual(stream.read().decode("utf-8"), "global-item")
		stream.close()

		tenant_token = Tenant.set("acme")
		try:
			stream = await self.provider.read("/Templates/item.json")
			self.assertEqual(stream.read().decode("utf-8"), "tenant-item")
			stream.close()

			authz_token = Authz.set(SimpleNamespace(CredentialsId="user1"))
			try:
				stream = await self.provider.read("/Templates/item.json")
				self.assertEqual(stream.read().decode("utf-8"), "personal-item")
				stream.close()
			finally:
				Authz.reset(authz_token)
		finally:
			Tenant.reset(tenant_token)

	async def test_list_overlay_only_directory(self):
		tenant_token = Tenant.set("acme")
		authz_token = Authz.set(SimpleNamespace(CredentialsId="user1"))
		try:
			items = await self.provider.list("/OverlayOnly/")
		finally:
			Authz.reset(authz_token)
			Tenant.reset(tenant_token)

		by_layer = {item.layers[0]: item.name for item in items}
		self.assertEqual(
			by_layer,
			{
				"0:personal": "/OverlayOnly/personal.json",
				"0:tenant": "/OverlayOnly/tenant.json",
			},
		)

	async def test_list_without_tenant_is_global_only(self):
		items = await self.provider.list("/Templates/")
		self.assertTrue(all(item.layers[0] == "0:global" for item in items))
		self.assertIn("/Templates/item.json", {item.name for item in items})

	def test_subscription_bases_for_tenant_target(self):
		bases = list(self.provider._iter_subscription_bases("tenant"))
		self.assertEqual(bases, [os.path.join(self.root, ".tenants", "acme")])

		bases = list(self.provider._iter_subscription_bases(("tenant", "acme")))
		self.assertEqual(bases, [os.path.join(self.root, ".tenants", "acme")])
