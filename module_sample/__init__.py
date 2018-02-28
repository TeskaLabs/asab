import logging

from asab.abc.module import Module

#

L = logging.getLogger(__name__)

#


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		L.info("Sample module loaded.")
