import logging

from ..abc import Module
from .service import LibraryService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
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
