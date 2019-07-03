
class Singleton(type):

	"""
The `singleton pattern <https://en.wikipedia.org/wiki/Singleton_pattern>`_ is a software design pattern that restricts the instantiation of a class to one object.

*Note*: The implementation idea is borrowed from "`Creating a singleton in Python <https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python>`_" question on StackOverflow.
	"""

	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

	@classmethod
	def delete(cls, singleton_cls):
		'''
		The method for an intentional removal of the singleton object.
		It shouldn't be used unless you really know what you are doing.

		One use case is a unit test, which removes an Application object after each iteration.
		'''
		del cls._instances[singleton_cls]
