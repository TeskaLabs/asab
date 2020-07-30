import logging
import asab

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		sttype = asab.Config.get('asab:storage', 'type')

		if sttype == 'inmemory':
			from .inmemory import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		elif sttype == 'mongodb':
			from .mongodb import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		elif sttype == "elasticsearch":
			from .elasticsearch import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		else:
			L.error("Unknown asab:storage type '{}'".format(sttype))
