import logging
import aiohttp.web

import asab

#

L = logging.getLogger(__name__)

#

#TODO: Configure cookie name
#TODO: Configure cookie http only / secure
#TODO: Configure cookie domain
#TODO: Configure max-age

class ServiceWebSession(asab.Service):

	def __init__(self, app, service_name, webservice, session_storage=None):
		super().__init__(app, service_name)

		webapp = webservice.WebApp

		# Construct session storage
		if session_storage is None:
			from .inmemstor import InMemorySessionStorage
			self.SessionStorage = InMemorySessionStorage(app)
		else:
			self.SessionStorage = session_storage

		# Add middleware to a webservice
		webapp.middlewares.append(
			session_middleware(
				self.SessionStorage
			)
		)


def session_middleware(storage):

	@aiohttp.web.middleware
	async def factory(request, handler):
		session = await storage.load(request)
		request['Session'] = session
		try:
			response = await handler(request)
			await storage.set(session, response)
			return response
		finally:
			await storage.store(session)

	return factory


