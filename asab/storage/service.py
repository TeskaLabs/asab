import abc
import asab


class StorageServiceABC(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)


	@abc.abstractmethod
	def upsertor(self, collection: str, obj_id=None, version: int = 0):
		'''
		If updating an existing object, please specify its `obj_id` and also `version` that you need to read from a storage upfront.
		If `obj_id` is None, we assume that you want to insert a new object and generate its new `obj_id`, `version` should be set to 0 (default) in that case.
		If you want to insert a new object with a specific `obj_id`, specify `obj_id` and set a version to 0.
			- If there will be a colliding object already stored in a storage, `execute()` method will fail on `DuplicateError`.

		:param collection: Name of collection to work with
		:param obj_id: Primary identification of an object in the storage (e.g. primary key)
		:param version: Specify a current version of the object and hence prevent byzantine faults. \
						You should always read the version from the storage upfront, prior using an upsertor. \
						That creates a soft lock on the record. It means that if the object is updated by other \
						component in meanwhile, your upsertor will fail and you should retry the whole operation. \
						The new objects should have a `version` set to 0.
		'''
		pass


	@abc.abstractmethod
	async def get(self, collection: str, obj_id) -> dict:
		"""
		Get object from collection

		:param collection: Collection to get from
		:param obj_id: Object identification
		:return: The object retrieved from a storage

		Raises:
			KeyError: If `obj_id` not found in `collection`
		"""
		pass


	@abc.abstractmethod
	async def get_by(self, collection: str, key: str, value):
		pass


	@abc.abstractmethod
	async def delete(self, collection: str, obj_id):
		pass
