import abc
import asab

class StorageServiceABC(asab.Service):
	
	def __init__(self, app, service_name):
		super().__init__(app, service_name)


	@abc.abstractmethod
	def upsertor(self, collection:str, obj_id=None, version=0):
		'''
		:param int version: Specify a current version of the object and hence prevent race conditions on updates. \
							If None, the check is skipped. \
							If 0, the insert operation is expected.
		'''
		pass


	@abc.abstractmethod
	async def get(self, collection:str, obj_id) -> dict:
		"""
		Get object from collection

		:param collection: Collection to get from
		:param obj_id: Object identification
		:return: dict -- The founded object

		Raises:
			KeyError: If `obj_id` not found in `collection`
		"""
		pass


	@abc.abstractmethod
	async def get_by(self, collection:str, key:str, value):
		pass


	@abc.abstractmethod
	async def delete(self, collection:str, obj_id):
		pass
