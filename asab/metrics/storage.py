
class Storage(object):

	def __init__(self):
		self.Tree = dict()


	def add(self, dimension: str):
		if dimension in self.Tree:
			raise RuntimeError("Metrics dimension already exists in the data storage")

		data = dict()
		self.Tree[dimension] = data
		return data


	def values(self):
		return self.Tree.values()
