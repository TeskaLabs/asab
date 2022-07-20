import io
import typing
import logging
import tempfile
import dataclasses
import urllib.parse

import aiohttp
import xml.dom.minidom

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


	def __init__(self, library, path):
		super().__init__(library)
		assert path[:6] == "azure+"

		self.URL = urllib.parse.urlparse(path[6:])
		self.Model = None  # Will be set by `_load_model` method
		self.Path = path

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
		L.info("AzureStorage library provider {} is connected.".format(self.Path))

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

		url = urllib.parse.urlunparse(urllib.parse.ParseResult(
			scheme=self.URL.scheme,
			netloc=self.URL.netloc,
			path=self.URL.path + path,
			params='',
			query=self.URL.query,
			fragment=''
		))

		async with aiohttp.ClientSession() as session:
			async with session.get(url) as resp:
				if resp.status == 200:
					# TODO: Use of resp.headers['Etag'] for a local cache

					# Load the response into the temporary file
					# ... that's to avoid storing the whole (and possibly large) file in the memory
					output = tempfile.TemporaryFile()
					async for chunk in resp.content.iter_chunked(16 * io.DEFAULT_BUFFER_SIZE):
						output.write(chunk)
				else:
					L.warning("Failed to get blob:\n{}".format(await resp.text()))
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
