import abc

class Module(abc.ABC):
	"""
	Abstract module class
	"""

	def __init__(self, app):
		pass


	# Lifecycle

	async def initialize(self, app):
		pass

	async def finalize(self, app):
		pass
