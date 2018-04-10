# This is the backend for ASAB Web UI Kit.
import os
import glob
import functools
import aiohttp.web


class StaticDirProvider(object):

	'''
To serve e.g. React app, add this to your asab.Application / async def initialize(self):

svc = self.get_service("asab.WebService")
webappdir = os.environ.get('WEBAPPDIR', 'webapp')
svc.addWebApp('/', webappdir)
	'''

	def __init__(self, websvc, root, path, index='index.html'):
		self.Path = path
		self.Index = index

		websvc.WebApp.router.add_get(root, self.index)

		# Read all files from path (build from React) and map them statically
		for fname in glob.glob(os.path.join(self.Path, '*')):
			if os.path.isfile(fname):
				websvc.WebApp.router.add_get(root+os.path.basename(fname), functools.partial(self.file, fname))
			elif os.path.isdir(fname):
				websvc.WebApp.router.add_static(root+os.path.basename(fname), path=fname)


	async def index(self, request):
		return aiohttp.web.FileResponse(os.path.join(self.Path, self.Index))


	async def file(self, fname, request):
		return aiohttp.web.FileResponse(fname)