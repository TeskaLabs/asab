
class DuplicateError(RuntimeError):

	def __init__(self, message, obj_id):
		super().__init__(message)
		self.ObjId = obj_id
