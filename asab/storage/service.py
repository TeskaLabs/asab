import abc
import asab

class StorageServiceABC(asab.Service):
	
	def __init__(self, app, service_name):
		super().__init__(app, service_name)


	@abc.abstractmethod
	def upsertor(self, collection:str, origObj=None):
		pass


	@abc.abstractmethod
	async def get(self, collection:str, pk):
		pass


	@abc.abstractmethod
	async def delete(self, collection:str, pk):
		pass
