

class Tenant(object):

	def __init__(self, tenant_id: str, params: dict = {}):

		self.Id = tenant_id
		self.Parameters = params

	def to_dict(self):

		return {
			'id': self.Id,
			'parameters': self.Parameters
		}
