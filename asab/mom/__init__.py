import logging
import asab

from .service import MOMService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
	}
)


class Module(asab.Module):
	'''
	Message-oriented middleware

	https://en.wikipedia.org/wiki/Message-oriented_middleware
	'''

	def __init__(self, app):
		super().__init__(app)
		self.service = MOMService(app, "asab.MOMService")
