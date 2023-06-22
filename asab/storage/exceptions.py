
class DuplicateError(RuntimeError):
	"""
	Raised when the key already exists in the same document.
	"""

	def __init__(self, message, obj_id, key_value=None):
		super().__init__(message)
		self.ObjId = obj_id
		self.KeyValue = key_value
