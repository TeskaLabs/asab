import logging
import asab

from .service import ProactorService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:proactor': {
			'max_workers': '0',
			'default_executor': True,
		}
	}
)


class Module(asab.Module):
	'''
	Proactor pattern based on loop.run_in_executor()

	https://en.wikipedia.org/wiki/Proactor_pattern
	'''

	def __init__(self, app):
		super().__init__(app)
		self.service = ProactorService(app, "asab.ProactorService")
