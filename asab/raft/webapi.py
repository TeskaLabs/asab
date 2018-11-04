import aiohttp
import asab.web
import asab.web.rest

class RaftWebApi(object):


	def __init__(self, app, rpc):
		self.App = app
		self.Root = '/raft'

		# Locate web service
		websvc = app.get_service("asab.WebService")	

		# Enable exception to JSON exception middleware
		websvc.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		websvc.WebApp.router.add_get('{}/status'.format(self.Root), self.status)
		websvc.WebApp.router.add_put('{}/client_request'.format(self.Root), self.client_request)


	async def status(self, request):
		raftsvc = self.App.get_service("asab.RaftService")
		status = await raftsvc.Client.status()
		return asab.web.rest.json_response(request, status)


	async def client_request(self, request):
		raftsvc = self.App.get_service("asab.RaftService")
		command = await request.json()
		result = await raftsvc.Client.client_request(command)
		return asab.web.rest.json_response(request, result)
