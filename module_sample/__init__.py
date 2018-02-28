import logging

from asab.abc.module import Module

from .service_sample import ServiceSample

#

L = logging.getLogger(__name__)

#


class Module(Module):

	def __init__(self, app):
		super().__init__(app)

		self.service_sample = ServiceSample(app)
		app.register_service("service_sample", self.service_sample)

		L.info("Sample module loaded.")
