import aiohttp
import asab.web
import asab.web.rest

class RaftWebApi(object):


	def __init__(self, app, rpc):
		self.App = app
		self.Root = '/raft'

		# Locate web service
		websvc = app.get_service("asab.WebService")	

		# Enable exception to JSON middleware
		websvc.WebApp.middlewares.append(asab.web.except_json_middleware)

		websvc.WebApp.router.add_get('{}/status'.format(self.Root), self.status)


	async def status(self, request):
		raftsvc = self.App.get_service("asab.RaftService")
		status = await raftsvc.Client.status()
		return asab.web.rest.json_response(request, status)

