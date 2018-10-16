import logging
import asab

from .service import LogManIOService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'logman.io': {
			'url': 'amqps://{username}:{password}@lm-ha-01.logman.io:5477/{virtualhost}',
			'username': 'testuser',
			'password': 'password',
			'virtualhost': 'playground',
			'routing_key': '',
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = LogManIOService(app, "asab.LogManIOService")
