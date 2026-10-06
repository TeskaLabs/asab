"""Overlay tests for LibsRegLibraryProvider after switching to FileSystemLibraryProvider."""

import logging
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import asab
import asab.abc

from asab.contextvars import Authz, Tenant
from asab.library.providers.filesystem import FileSystemLibraryProvider
from asab.library.providers.libsreg import LibsRegLibraryProvider


LIBSREG_URL = "libsreg+https://libsreg.example.com/my-library"


class _Library(object):
	def __init__(self, app):
		self.App = app

	async def _set_ready(self, provider):
		pass


def _write_file(root, library_path, content):
	full_path = os.path.join(root, library_path.lstrip("/"))
	os.makedirs(os.path.dirname(full_path), exist_ok=True)
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(content)


class TestLibsRegLibraryProvider(unittest.IsolatedAsyncioTestCase):

	async def asyncSetUp(self):
		self.tmpdir = tempfile.TemporaryDirectory()
		self.content_root = os.path.join(self.tmpdir.name, "content")
		os.makedirs(self.content_root, exist_ok=True)

		_write_file(self.content_root, "/Templates/item.json", "global-item")
		_write_file(self.content_root, "/Templates/global-only.json", "global-only")
		_write_file(self.content_root, "/.tenants/acme/Templates/item.json", "tenant-item")
		_write_file(self.content_root, "/.tenants/acme/Templates/tenant-only.json", "tenant-only")
		_write_file(self.content_root, "/.personal/acme/user1/Templates/item.json", "personal-item")
		_write_file(self.content_root, "/.personal/acme/user1/Templates/personal-only.json", "personal-only")

		self.App = asab.Application(args=[], modules=[])
		# Avoid scheduling a real pull (and the un-awaited coroutine it would create).
		with mock.patch.object(LibsRegLibraryProvider, "_periodic_pull", return_value=None):
			self.provider = LibsRegLibraryProvider(
				_Library(self.App),
				LIBSREG_URL,
				0,
				source=LIBSREG_URL,
				repodir=self.tmpdir.name,
			)

	async def asyncTearDown(self):
		await self.provider.finalize(self.App)
		asab.abc.singleton.Singleton.delete(self.App.__class__)
		self.App = None
		self.tmpdir.cleanup()
		logging.getLogger().handlers = []

	async def test_uses_full_filesystem_provider(self):
		self.assertIsInstance(self.provider, FileSystemLibraryProvider)
		self.assertEqual(self.provider.BasePath, self.content_root)

	async def test_read_global_without_tenant_context(self):
		stream = await self.provider.read("/Templates/item.json")
		self.assertIsNotNone(stream)
		self.assertEqual(stream.read().decode("utf-8"), "global-item")
		stream.close()

	async def test_read_prefers_tenant_overlay(self):
		tenant_token = Tenant.set("acme")
		try:
			stream = await self.provider.read("/Templates/item.json")
			self.assertEqual(stream.read().decode("utf-8"), "tenant-item")
			stream.close()
		finally:
			Tenant.reset(tenant_token)

	async def test_read_prefers_personal_overlay(self):
		tenant_token = Tenant.set("acme")
		authz_token = Authz.set(SimpleNamespace(CredentialsId="user1"))
		try:
			stream = await self.provider.read("/Templates/item.json")
			self.assertEqual(stream.read().decode("utf-8"), "personal-item")
			stream.close()
		finally:
			Authz.reset(authz_token)
			Tenant.reset(tenant_token)

	async def test_list_concatenates_personal_tenant_global(self):
		tenant_token = Tenant.set("acme")
		authz_token = Authz.set(SimpleNamespace(CredentialsId="user1"))
		try:
			items = await self.provider.list("/Templates/")
		finally:
			Authz.reset(authz_token)
			Tenant.reset(tenant_token)

		by_layer = {}
		for item in items:
			by_layer.setdefault(item.layers[0], []).append(item.name)

		self.assertEqual(list(by_layer.keys()), ["0:personal", "0:tenant", "0:global"])
		self.assertEqual(
			set(by_layer["0:personal"]),
			{"/Templates/item.json", "/Templates/personal-only.json"},
		)
		self.assertEqual(
			set(by_layer["0:tenant"]),
			{"/Templates/item.json", "/Templates/tenant-only.json"},
		)
		self.assertEqual(
			set(by_layer["0:global"]),
			{"/Templates/item.json", "/Templates/global-only.json"},
		)

	async def test_subscribe_records_path_without_using_inotify(self):
		self.assertIsNone(self.provider.FD)
		await self.provider.subscribe("/Templates/")
		self.assertIn("/Templates/", self.provider.SubscribedPaths)
		self.assertEqual(self.provider.WDs, {})
