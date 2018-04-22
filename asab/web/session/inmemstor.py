import uuid
import logging

from .storage import SessionStorage
from .cookies import CookieSessionMixIn

#

L = logging.getLogger(__name__)

#

class InMemorySessionStorage(SessionStorage, CookieSessionMixIn):


	def __init__(self, app, session_class, max_age=60*15, cookie_name='SESSID'):
		super().__init__(app, max_age=max_age, session_class=session_class)
		self.set_cookie_name(cookie_name)

		self.Sessions = {}

		app.PubSub.subscribe("Application.tick/10!", self._on_tick)


	async def load(self, request):
		session_id = self.get_session_id_from_request(request)
		if session_id is not None:
			session = self.Sessions.get(session_id)
			if session is not None:
				if session.is_expired():
					session = None
				else:
					return session

			L.warning("Invalid session id '{}'".format(session_id))
		
		return await self.create(request)


	async def set(self, session, response):
		if session.is_new():
			
			while True:
				session_id = uuid.uuid4().hex
				if session_id not in self.Sessions:
					session.set_id(session_id)
					break

			self.Sessions[session.Id] = session
			self.set_session_to_response(session, response)


	async def delete(self, session):
		session_p = self.Sessions.pop(session.Id)
		assert session_p == session


	async def store(self, session):
		session.reset()


	async def _on_tick(self, message_type):
		# Find expired session and remove them
		expired_sessions = []
		for session in self.Sessions.values():
			if session.is_expired():
				expired_sessions.append(session)

		for session in expired_sessions:
			await self.delete(session)

