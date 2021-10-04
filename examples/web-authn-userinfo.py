import logging
import re

import aiohttp

import asab
import asab.web
import asab.web.rest
import asab.web.authn
import asab.web.authn.oauth
import asab.web.openidconnect

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
		container = websvc.WebContainer

		# Load the OIDC module
		self.add_module(asab.web.openidconnect.Module)
		self.oidc_service = self.get_service("asab.OpenIDConnectService")

		# Enable exception to JSON exception middleware
		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		container.WebApp.router.add_get('/user', self.user)

	# TODO: Use userinfo decorator
	async def user(self, request):
		userinfo = None
		authorization_header = request.headers.get(aiohttp.hdrs.AUTHORIZATION, None)
		if authorization_header is not None:
			authorization_match = re.compile(r"^\s*Bearer ([A-Za-z0-9\-\.\+_~/=]*)").match(authorization_header)
			if authorization_match is not None:
				access_token = authorization_match.group(1)
				userinfo = await self.oidc_service.userinfo(access_token)

		if userinfo is not None:
			username = userinfo.get("preferred_username")
			email = userinfo.get("email")
			return asab.web.rest.json_response(request=request, data={
				"message": "Hello {}, your email address is {}.".format(username, email),
				"result": "OK"
			})

		return asab.web.rest.json_response(request=request, data={
			"result": "FAILED"
		})


if __name__ == '__main__':
	app = MyOAuthSecuredApplication()
	app.run()
