import io
import typing
import logging
import tempfile
import dataclasses
import os
import struct
import urllib.parse

import aiohttp
import xml.dom.minidom

from ...config import Config
from .abc import LibraryProviderABC
from ..item import LibraryItem

#

L = logging.getLogger(__name__)


#


class AzureStorageLibraryProvider(LibraryProviderABC):
	'''
	AzureStorageLibraryProvider is a library provider that reads
	from an Microsoft Azure Storage container.

	Configure by:

	azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER

	If Container Public Access Level is not set to "Public access",
	then "Access Policy" must be created with "Read" and "List" permissions
	and "Shared Access Signature" (SAS) query string must be added to a URL in a configuration:

	azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER?sv=2020-10-02&si=XXXX&sr=c&sig=XXXXXXXXXXXXXX

	'''
	ConfigDefaults = {
		"master_timeout": 30,
		"use_cache": "yes",
		"cache_dir": ""
	}

	def __init__(self, library, path):
		super().__init__(library)
		assert path[:6] == "azure+"

		self.URL = urllib.parse.urlparse(path[6:])
		self.Model = None  # Will be set by `_load_model` method
		self.UseCache = Config.getboolean("use_cache")
		self.ETag = None
		self.Path = path
		self.CachePath = None
		if self.UseCache is True:
			cache_path = asab.Config.get("cache_dir", "").strip()
			if len(cache_path) == 0 and "general" in asab.Config and "var_dir" in asab.Config["general"]:
				cache_path = os.path.abspath(asab.Config["general"]["var_dir"])
				self.CachePath = os.path.join(cache_path, "azure_{}.cache")
			else:
				self.UseCache = False
				L.warning("No cache path specified. Cache disabled.")
		self.App.TaskService.schedule(self._start())

	async def _start(self):
		await self._load_model()
		await self._set_ready()

	# TODO: Call this periodically
	async def _load_model(self):
		url = urllib.parse.urlunparse(urllib.parse.ParseResult(
			scheme=self.URL.scheme,
			netloc=self.URL.netloc,
			path=self.URL.path,
			params='',
			query=self.URL.query + "&restype=container&comp=list",
			fragment=''
		))

		async with aiohttp.ClientSession() as session:
			async with session.get(url) as resp:
				if resp.status == 200:
					content = await resp.text()
				else:
					L.warning("Failed to list blobs:\n{}".format(await resp.text()))
					return

		model = AzureDirectory("/", sub=dict())

		dom = xml.dom.minidom.parseString(content)
		for blob in dom.getElementsByTagName("Blob"):
			path = get_xml_text(blob.getElementsByTagName("Name"))

			path = path.split('/')
			curmodel = model
			for i in range(len(path) - 1):
				newmodel = curmodel.sub.get(path[i])
				if newmodel is None:
					curmodel.sub[path[i]] = newmodel = AzureDirectory(
						name='/' + '/'.join(path[:i + 1]),
						sub=dict()
					)

				curmodel = newmodel

			curmodel.sub[path[-1]] = AzureItem(
				name='/' + '/'.join(path)
			)

		self.Model = model
		L.info("is connected.", struct_data={'path': self.Path})

	async def list(self, path: str) -> list:
		if self.Model is None:
			L.warning("Azure Storage library provider is not ready. Cannot list {}".format(path))
			raise RuntimeError("Not ready")

		assert path[:1] == '/'
		assert '//' not in path
		assert len(path) == 1 or path[-1:] != '/'

		if path == '/':
			pathparts = []
		else:
			pathparts = path.split("/")[1:]

		curmodel = self.Model
		for p in pathparts:
			curmodel = curmodel.sub.get(p)
			if curmodel is None:
				raise KeyError("Not '{}' found".format(path))
			if curmodel.type != 'dir':
				raise KeyError("Not '{}' found".format(path))

		items = []
		for i in curmodel.sub.values():
			items.append(LibraryItem(
				name=i.name,
				type=i.type,
				providers=[self],
			))

		return items

	def load_from_cache(self):
		"""
		Load the lookup data (bytes) from cache.
		"""
		if self.UseCache is False:
			return False
		# Load the ETag from cached file, if have one
		if not os.path.isfile(self.CachePath):
			L.warning("Cache '{}': not a file".format(self.CachePath))
			return False

		if not os.access(self.CachePath, os.R_OK):
			L.warning("Cannot read cache from '{}'".format(self.CachePath))
			return False

		try:
			with open(self.CachePath, 'rb') as f:
				tlen, = struct.unpack(r"<L", f.read(struct.calcsize(r"<L")))
				etag_b = f.read(tlen)
				self.ETag = etag_b.decode('utf-8')
				f.read(1)
				data = f.read()
			return data
		except Exception as e:
			L.warning("Failed to read content of lookup cache '{}' from '{}': {}".format(self.Id, self.CachePath, e))
			os.unlink(self.CachePath)
		return False

	def save_to_cache(self, data):
		if self.UseCache is False:
			return
		dirname = os.path.dirname(self.CachePath)
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		with open(self.CachePath, 'wb') as fo:
			# Write E-Tag and '\n'
			etag_b = self.ETag.encode('utf-8')
			fo.write(struct.pack(r"<L", len(etag_b)) + etag_b + b'\n')

			# Write Data
			fo.write(data)

	async def read(self, path: str) -> typing.IO:
		assert path[:1] == '/'
		assert '//' not in path
		assert len(path) == 1 or path[-1:] != '/'

		url = urllib.parse.urlunparse(urllib.parse.ParseResult(
			scheme=self.URL.scheme,
			netloc=self.URL.netloc,
			path=self.URL.path + path,
			params='',
			query=self.URL.query,
			fragment=''
		))

		async with aiohttp.ClientSession() as session:
			try:
				async with session.get(url) as resp:
					if resp.status == 200:
						# read data
						self.ETag = resp.headers.get('ETag')
						data = await resp.read()
						if self.CachePath is not None:
							self.save_to_cache(data)
						# TODO: Use of resp.headers['Etag'] for a local cache

						# Load the response into the temporary file
						# ... that's to avoid storing the whole (and possibly large) file in the memory
						output = tempfile.TemporaryFile()
						async for chunk in resp.content.iter_chunked(16 * io.DEFAULT_BUFFER_SIZE):
							output.write(chunk)
					else:
						L.warning("Failed to get blob:\n{}".format(await resp.text()))
						return None
			except aiohttp.ClientConnectorError as e:
				L.warning("Failed to contact azure master at '{}': {}".format(self.URL, e))
				return self.load_from_cache()

		# Rewind the file so the reader can start consuming from the beginning
		output.seek(0)
		return output


@dataclasses.dataclass
class AzureDirectory:
	name: str
	sub: dict
	type: str = "dir"


@dataclasses.dataclass
class AzureItem:
	name: str
	type: str = "item"


def get_xml_text(nodelist):
	rc = []
	for node in nodelist:
		for textnode in node.childNodes:
			if textnode.nodeType == textnode.TEXT_NODE:
				rc.append(textnode.data)
	return ''.join(rc)
