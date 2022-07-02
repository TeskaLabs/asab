import logging

from ..abc import Module
from ..config import Config

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

		from .service import LibraryService
		self.service = LibraryService(self.App, "asab.LibraryService")


__all__ = [
	"Module",
]
