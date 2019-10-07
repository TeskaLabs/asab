import logging

import asab
import asab.web
import asab.web.rest
import asab.web.authn
import asab.web.authn.oauth

#

L = logging.getLogger(__name__)

#


class MyOAuthSecuredApplication(asab.Application):
	"""
	MyOAuthSecuredApplication serves endpoints, which can only access clients authorized via OAuth 2.0 server.

	In order to try the example with GitHub, follow this guide to request an access token.
	You will need to create your mock GitHub OAuth application and call authorize and access_token endpoints,
	as the guide suggest:
	https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#web-application-flow

	Then access the MyOAuthSecuredApplication user endpoint via:

	curl "http://127.0.0.1:8080/user" -H "Authorization: Bearer github.com-<YOUR_ACCESS_TOKEN>"

	The following message should then be displayed:

	<YOUR_GITHUB_EMAIL>, you have accessed our secured "user" endpoint.

	"""

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'example:oauth')

		# Add middleware for authentication via oauth2
		container.WebApp.middlewares.append(
			asab.web.authn.authn_middleware_factory(self,
				"oauth2client",
				methods=[
					# Use GitHub OAuth provider
					asab.web.authn.oauth.GitHubOAuthMethod(),
				],
			)
		)

		# Enable exception to JSON exception middleware
		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Register useful OAuth endpoints
		asab.web.authn.oauth.add_oauth_client(container=container, proxies=[asab.web.authn.oauth.OAuthProxy(config={
				"oauth_server_id": "github.com",
				"token_url": "https://github.com/login/oauth/access_token",
				"identity_url": "https://api.github.com/user",
			})])

		# Add a route
		container.WebApp.router.add_get('/user', self.user)

	@asab.web.authn.authn_required_handler
	async def user(self, request, *, identity):
		return asab.web.rest.json_response(request=request, data={
			'message': '"{}", you have accessed our secured "user" endpoint.'.format(identity),
		})


if __name__ == '__main__':
	app = MyOAuthSecuredApplication()
	app.run()
