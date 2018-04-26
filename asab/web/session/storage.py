import abc


class SessionStorage(abc.ABC):


	def __init__(self, app, max_age, session_class):
		self.App = app
		self.MaxAge = max_age
		self.SessionClass = session_class


	@abc.abstractmethod
	async def load(self, request):
		'''
		Load a session object from a persistent store
		or create a new one using create() method, if needed
		'''
		raise NotImplemented()


	@abc.abstractmethod
	def set(self, session, response):
		'''
		Set session object reference to a response
		'''
		raise NotImplemented()


	@abc.abstractmethod
	async def delete(self, session):
		'''
		Delete session object from a persistent store
		'''
		raise NotImplemented()


	@abc.abstractmethod
	async def store(self, session):
		'''
		Store session object to persistent store (if needed)
		'''
		raise NotImplemented()


	async def create(self, request):
		return self.SessionClass(self, id=None, new=True, max_age=self.MaxAge)
