# This is the backend for ASAB Web UI Kit.
import os
import glob
import functools
import aiohttp.web


class StaticDirProvider(object):

	def __init__(self, websvc, root, path, index='index.html'):
		self.Path = path
		self.Index = index
		self.Root = root.rstrip('/')

		websvc.WebApp.router.add_get(self.Root if len(self.Root) > 0 else '/', self._index)

		# Read all files from path (build from React) and map them statically
		for fname in glob.glob(os.path.join(self.Path, '*')):
			if os.path.isfile(fname):
				websvc.WebApp.router.add_get(self.Root + '/' + os.path.basename(fname), functools.partial(self._file, fname))
			elif os.path.isdir(fname):
				websvc.WebApp.router.add_static(self.Root + '/' + os.path.basename(fname), path=fname)


	async def _index(self, request):
		return aiohttp.web.FileResponse(os.path.join(self.Path, self.Index))


	async def _file(self, fname, request):
		return aiohttp.web.FileResponse(fname)
