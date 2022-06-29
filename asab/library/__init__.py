import logging

from ..abc.module import Module
#

L = logging.getLogger(__name__)

#


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.App = app
		from .service import LibraryService
		self.service = LibraryService(self.App, "asab.LibraryService")

	__all__ = [
		"Module",
	]
