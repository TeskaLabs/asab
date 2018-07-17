import logging
import asab

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'inmemory',
		}
	}
)


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

		else:
			L.error("Unknown asab:storage type '{}'".format(sttype))
