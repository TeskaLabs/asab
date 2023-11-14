import logging
import asab

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		# old configuration format [asab:storage]
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

		# new configuration format
		elif sttype is None:
			# [elasticsearch]
			if asab.Config.has_section('elasticsearch'):
				from .elasticsearch import StorageService
				self.Service = StorageService(app, "asab.StorageService", config_section_name='elasticsearch')

		else:
			L.error("Unknown asab:storage type '{}' or unsupported configuration format".format(sttype))
