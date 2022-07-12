import logging
import asab

#

L = logging.getLogger(__name__)

#


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		sttype = asab.Config.get('asab:storage', 'type')

		if 'inmemory' in sttype:
			from .inmemory import StorageService
			self.InMemoryStorageService = StorageService(app, "asab.InMemoryStorageService")

		if 'mongodb' in sttype:
			print("mongo initialized")
			from .mongodb import StorageService
			self.MongoDBStorageService = StorageService(app, "asab.MongoDBStorageService")

		if "elasticsearch" in sttype:
			from .elasticsearch import StorageService
			self.ElasticSearchStorageService = StorageService(app, "asab.ElasticSearchStorageService")

		else:
			L.error("Unknown asab:storage type '{}'".format(sttype))
