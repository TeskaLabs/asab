import os
import asab
import asab.web
import asab.web.rest

#


class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		listen = asab.Config["asab:web"]["listen"]
		self.Container = self._initialize_web(app, listen)

	def _initialize_web(self, app, listen):
		websvc = app.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(
			websvc, "asab:web",
			config={"listen": listen}
		)
		# TODO: refactor to use custom config section, instead of explicitly passing "listen" param?

		# Add routes
		container.WebApp.router.add_get('/asab/v1/environ', self.environ)
		container.WebApp.router.add_get('/asab/v1/config', self.config)

		return container


	async def environ(self, request):
		return asab.web.rest.json_response(request, dict(os.environ))


	async def config(self, request):
		# Copy the config and erase all passwords
		result = {}
		for section in asab.Config.sections():
			result[section] = {}
			# Access items in the raw mode (they are not interpolated)
			for option, value in asab.Config.items(section, raw=True):
				if section == "passwords":
					result[section][option] = "***"
				else:
					result[section][option] = value
		return asab.web.rest.json_response(request, result)
