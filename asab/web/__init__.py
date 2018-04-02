import logging
import asab

from .service_webapp import ServiceWebApp

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:web': {
			'listen': '0.0.0.0 8080', # Can be multiline
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = ServiceWebApp(app, "asab.WebService")
