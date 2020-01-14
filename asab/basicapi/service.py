import os
import asab
import asab.web
import asab.web.rest
from .log import APIHandler
import logging

#

buffer = []

##

L = logging.getLogger(__name__)

##


class ApiService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

		listen = asab.Config["general"]["basicapi"]

		self.Container = self._initialize_web(app, listen)

	def _initialize_web(self, app, listen):

		websvc = app.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(
			websvc, 'bspump:web',
			config={"listen": listen}
		)
		# TODO: Logging level configurable via config file
		self.APILogHandler = APIHandler(level=logging.NOTSET, storage=buffer)
		self.format = logging.Formatter("%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s")
		self.APILogHandler.setFormatter(self.format)
		self.Logging.RootLogger.addHandler(self.APILogHandler)

		# Add routes
		container.WebApp.router.add_get('/basicapi', basicapi)
		container.WebApp.router.add_get('/logs', logs)

		return container


async def basicapi(request):
	return asab.web.rest.json_response(request, dict(os.environ))


async def logs(request):
	return asab.web.rest.json_response(request, buffer)
