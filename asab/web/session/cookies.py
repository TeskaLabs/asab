import time

class CookieSessionMixIn(object):

	'''
	This mixin allows to store session id in browser Cookies
	'''

	def set_cookie_name(self, cookie_name):
		self.CookieName = cookie_name


	def get_session_id_from_request(self, request):
		return self._get_cookie(request)


	def set_session_to_response(self, session, response):
		assert(session.Id is not None)
		self._set_cookie(response, session.Id, max_age=session.MaxAge)



	def _get_cookie(self, request):
		cookie = request.cookies.get(self.CookieName)
		return cookie


	def _set_cookie(self, response, cookie_data, max_age=None):
		params = {} #dict(self._cookie_params)
		if max_age is not None:
			params['max_age'] = max_age
			params['expires'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(time.time() + max_age))

		if not cookie_data:
			response.del_cookie(self.CookieName, domain=params["domain"], path=params["path"])
		else:
			response.set_cookie(self.CookieName, cookie_data, **params)
