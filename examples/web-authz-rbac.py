import logging

import asab
import asab.web
import asab.web.authz
import asab.web.rest
import asab.web.tenant

#

L = logging.getLogger(__name__)

#


class MyRBACSecuredApplication(asab.Application):
	"""
	MyRBACSecuredApplication serves endpoints, which are checked for tenant authorization rights using SeaCat Auth RBAC.

	Test by:

	1.) Run SeaCat Auth at: http://localhost:8081
	2.) Perform OAuth authentication to obtain access token
	3.) Run: curl -H "Authorization: <ACCESS_TOKEN>" http://localhost:8089/cars
	"""

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'example:rbac', config={"listen": "0.0.0.0 8089"})

		# Add authz service
		# It is required by asab.web.authz.required decorator
		authz_service = asab.web.authz.AuthzService(self)
		container.WebApp.middlewares.append(
			asab.web.authz.authz_middleware_factory(self, authz_service)
		)

		# Enable exception to JSON exception middleware
		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		container.WebApp.router.add_get('/cars', self.get_cars)

	@asab.web.authz.required("car:list")
	async def get_cars(self, request):
		cars = ["Skoda", "Volvo", "Kia"]
		return asab.web.rest.json_response(request=request, data=cars)


if __name__ == '__main__':
	app = MyRBACSecuredApplication()
	app.run()
