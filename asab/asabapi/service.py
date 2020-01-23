import os
import asab
import asab.web
import asab.web.rest

#


class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		listen = asab.Config["general"]["asabapi"]

		self.Container = self._initialize_web(app, listen)

	def _initialize_web(self, app, listen):

		websvc = app.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(
			websvc, "",
			config={"listen": listen}
		)
		# TODO: refactor to use custom config section, instead of explicitly passing "listen" param?

		# Add routes
		container.WebApp.router.add_get('/asab/environ', environ)

		container.WebApp.router.add_get('/asab/config', config)

		return container


async def environ(request):
	return asab.web.rest.json_response(request, dict(os.environ))


async def config(request):
	return asab.web.rest.json_response(request, {s: dict(asab.Config.items(s)) for s in asab.Config.sections()})
