import abc

class Module(abc.ABC):
	"""
	Abstract module class
	"""

	def __init__(self, app):
		pass


	# Lifecycle

	async def initialize(self):
		pass

	#TODO: Consider adding lifecycle methods as in Application
