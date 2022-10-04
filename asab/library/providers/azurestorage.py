import os
import io
import typing
import hashlib
import logging
import tempfile
import dataclasses
import urllib.parse
import xml.dom.minidom

import aiohttp

from ...config import Config
from ..item import LibraryItem
from .abc import LibraryProviderABC

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

	def __init__(self, library, path):
		super().__init__(library)
		assert path[:6] == "azure+"

		self.URL = urllib.parse.urlparse(path[6:])
		self.Model = None  # Will be set by `_load_model` method
		self.Path = path

		self.CacheDir = Config.get("library", "azure_cache")
		if self.CacheDir == 'false':
			self.CacheDir = None
		elif self.CacheDir == 'true':
			self.CacheDir = os.path.join(tempfile.gettempdir(), "asab.library.azure.{}".format(hashlib.sha256(path.encode('utf-8')).hexdigest()))

		# Ensure that the case directory exists
		if self.CacheDir is not None:
			try:
				os.makedirs(self.CacheDir)
			except FileExistsError:
				pass  # Cache directory already exists

		self.App.TaskService.schedule(self._start())


	async def _start(self):
		await self._load_model()
		if self.Model is not None:
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
					err = await resp.text()
					L.warning("Failed to list blobs from `{}`:\n{}".format(url, err))
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

		# TODO: If the cache is active, remove items from the cache that:
		# 1) are not in the list
		# 2) their etag differs

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


	async def read(self, path: str) -> typing.IO:

		assert path[:1] == '/'
		assert '//' not in path
		assert len(path) == 1 or path[-1:] != '/'

		headers = {}

		pathhash = hashlib.sha256(path.encode('utf-8')).hexdigest()
		cachefname = os.path.join(self.CacheDir, pathhash)
		if self.CacheDir is not None:
			try:
				with open(cachefname + '.etag', "r") as etagf:
					etag = etagf.read()
				# We found a local cached file with the etag, we will use that in the request
				# if the request returns "304 Not Modified" then we will ship the local version of the file
				headers['If-None-Match'] = etag
			except FileNotFoundError:
				pass


		url = urllib.parse.urlunparse(urllib.parse.ParseResult(
			scheme=self.URL.scheme,
			netloc=self.URL.netloc,
			path=self.URL.path + path,
			params='',
			query=self.URL.query,
			fragment=''
		))

		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as resp:
				if resp.status == 200:

					etag = resp.headers.get('ETag')

					if self.CacheDir is not None and etag is not None:
						output = open(cachefname, "w+b")

						with open(cachefname + '.etag', "w") as etagf:
							etagf.write(etag)

					else:
						# Store the response into the temporary file
						# ... that's to avoid storing the whole (and possibly large) file in the memory
						output = tempfile.TemporaryFile()

					async for chunk in resp.content.iter_chunked(16 * io.DEFAULT_BUFFER_SIZE):
						output.write(chunk)

				elif resp.status == 304 and self.CacheDir is not None:  # 304 is Not Modified
					# The file should be read from cache
					output = open(cachefname, "r+b")

				else:
					L.warning("Failed to get blob:\n{}".format(await resp.text()), struct_data={'status': resp.status})
					return None

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
