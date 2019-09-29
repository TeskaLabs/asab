import logging
import json

import asab
import asab.web
import asab.web.rest
import asab.web.authn

#

L = logging.getLogger(__name__)

#


class MyOAuthSecuredApplication(asab.Application):
	"""
	MyOAuthSecuredApplication serves endpoints, which can only access clients authorized via OAuth 2.0 server.
	The OAuth 2.0 server is specified in the `oauth_user_info_url` configuration option below.

	In order to try the example with GitHub, follow this guide to request an access token.
	You will need to create your mock GitHub OAuth application and call authorize and access_token endpoints,
	as the guide suggest:
	https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#web-application-flow

	Then access the MyOAuthSecuredApplication user endpoint via:

	curl "http://127.0.0.1:8080/user" -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

	The following message should then be displayed:

	<YOUR_GITHUB_LOGIN>, you have accessed our secured "user" endpoint.

	"""

	asab.Config.add_defaults({
		'general': {
			'oauth_user_info_url': 'https://api.github.com/user'  # Any OAuth 2.0 service can be used, including a custom one running on localhost.
		}
	})

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'example:oauth')

		# Add middleware for authentication via oauth2
		container.WebApp.middlewares.append(
			asab.web.authn.authn_middleware_factory(self, "oauth2client", asab.Config["general"]["oauth_user_info_url"])
		)

		# Enable exception to JSON exception middleware
		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		container.WebApp.router.add_get('/user', self.user)

	@asab.web.authn.authn_required_handler
	async def user(self, request, *, identity):
		return asab.web.rest.json_response(request=request, data={
			'message': '"{}", you have accessed our secured "user" endpoint.'.format(
				authn_identity.get("login", json.dumps(authn_identity))
			),
		})


if __name__ == '__main__':
	app = MyOAuthSecuredApplication()
	app.run()
