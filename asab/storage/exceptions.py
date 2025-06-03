
class DuplicateError(RuntimeError):
	"""
	Raised when the key already exists in the same document.
	"""

	def __init__(self, message, obj_id, key_value=None):
		super().__init__(message)
		self.ObjId = obj_id
		self.KeyValue = key_value


class DryRunAbort(Exception):
	"""
	Raised when a transaction is aborted due to a DRY_RUN context being true.
	"""
	def __init__(self, obj_id):
		self.ObjID = obj_id
		super().__init__(obj_id)
