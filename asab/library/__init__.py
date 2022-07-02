import logging

from ..abc import Module
from ..config import Config
from .service import LibraryService

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'library': {
			'path': 'zk:///library'
		}
	}
)


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.App = app
		self.service = LibraryService(self.App, "asab.LibraryService")
