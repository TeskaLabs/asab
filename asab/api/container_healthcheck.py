import logging
from aiohttp.web import HTTPServiceUnavailable, HTTPOk


##


L = logging.getLogger(__name__)


##


class ContainerHealthCheckHandler(logging.Handler):
	def __init__(self, app):
		super().__init__()
		app.PubSub.subscribe("Application.exit!", self.application_exiting)
		app.PubSub.subscribe("Application.stop!", self.application_exiting)
		self.Exiting = False


	async def docker(self, request):
		if self.Exiting is False:
			raise HTTPOk
		raise HTTPServiceUnavailable

	async def application_exiting(self, x):
		self.Exiting = True
