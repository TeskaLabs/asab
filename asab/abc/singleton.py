
class Singleton(type):

	"""
	The singleton pattern is a software design pattern that restricts the instantiation of a class to one object.
	More at https://en.wikipedia.org/wiki/Singleton_pattern
	Implementation idea is from https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python

	Usage:

	class MyClass(metaclass=Singleton):
		...

	"""

	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]
