
class DuplicateError(RuntimeError):

	def __init__(self, message, obj_id, key_value=None):
		super().__init__(message)
		self.ObjId = obj_id
		self.KeyValue = key_value
