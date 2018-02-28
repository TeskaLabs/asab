import logging
import asab

from .service_sample import ServiceSample

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)

		self.service_sample = ServiceSample(app)
		app.register_service("service_sample", self.service_sample)

		L.info("Sample module loaded.")
