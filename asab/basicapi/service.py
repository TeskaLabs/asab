import os
import asyncio
import aiohttp.web
import asab
import asab.web
import asab.web.rest

#

class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		listen = asab.Config["general"]["basicapi"]

		self.Container = self._initialize_web (app, listen)


	def _initialize_web(self, app, listen):


		websvc = app.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'bspump:web', config={"listen": listen})

		# Add routes
		container.WebApp.router.add_get('/basicapi', basicapi)

		return container


async def basicapi(request):
	return asab.web.rest.json_response(request, dict(os.environ))