import logging
from .. import Config, Module

from .service import LogManIOService

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'logman.io': {
			'url': 'amqps://{username}:{password}@feed.logman.io:5477/{virtualhost}',
			'username': 'testuser',
			'password': 'password',
			'virtualhost': 'playground',
			'routing_key': '',
		}
	}
)


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = LogManIOService(app, "asab.LogManIOService")
