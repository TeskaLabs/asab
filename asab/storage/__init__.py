import logging
import asab

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		sttype = asab.Config.get('asab:storage', 'type', fallback=None)

		if sttype == 'inmemory':
			from .inmemory import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		elif sttype == 'mongodb':
			from .mongodb import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		elif sttype == "elasticsearch":
			from .elasticsearch import StorageService
			self.Service = StorageService(app, "asab.StorageService")

		elif sttype is None:
			L.critical("Missing configuration for [asab:storage] type.")
			raise SystemExit("Exit due to a critical configuration error.")

		else:
			L.critical("Unknown configuration type '{}' in [asab:storage].".format(sttype))
			raise SystemExit("Exit due to a critical configuration error.")
