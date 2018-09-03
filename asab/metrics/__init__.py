import logging
import asab

from .service import MetricsService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:metrics': {
			'target': '', # Can be multiline
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = MetricsService(app, "asab.MetricsService")
