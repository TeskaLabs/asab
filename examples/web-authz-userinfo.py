import logging

import asab
import asab.web
import asab.web.authz
import asab.web.rest
import asab.web.tenant

#

L = logging.getLogger(__name__)

#


class MyApplication(asab.Application):
	"""
	MyApplication serves endpoints which may use user info obtained from the authentication server.

	Run this app with config file:
	```sh
	python3 examples/web-authz-userinfo.py -c examples/web-authz-userinfo.conf
	```

	Test by:
	1) Run SeaCat Auth at: http://localhost:8081
	2) Perform OAuth authentication to obtain access token
	3) Run: curl -H "Authorization: <ACCESS_TOKEN>" http://localhost:8089/user
	"""

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, "web")

		# Add authz service
		# It is required by asab.web.authz.required decorator
		authz_service = asab.web.authz.AuthzService(self)
		container.WebApp.middlewares.append(
			asab.web.authz.authz_middleware_factory(self, authz_service)
		)

		# Enable exception to JSON exception middleware
		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		container.WebApp.router.add_get('/user', self.get_userinfo)

	@asab.web.authz.userinfo_handler
	async def get_userinfo(self, request, *, userinfo):
		message = "Hi {}, your email is {}".format(
			userinfo.get("preferred_username"),
			userinfo.get("email")
		)
		return asab.web.rest.json_response(request=request, data={"message": message})


if __name__ == '__main__':
	app = MyApplication()
	app.run()
