#!/usr/bin/env python3
import asab.web.rest
import asab.web.auth
import typing

if "web" not in asab.Config:
	asab.Config["web"] = {
		# Set up a web container listening at port 8080
		"listen": "8080"
	}

if "auth" not in asab.Config:
	asab.Config["auth"] = {
		# Disable or enable all authentication and authorization, or switch into MOCK mode.
		# When disabled, the `resources` and `userinfo` handler arguments are set to `None`.
		"enabled": "mock",  # Mock authorization, useful for debugging.
		# "enabled": "yes",   # Authorization is enabled.
		# "enabled": "no",   # Authorization is disabled.

		# Activating the mock mode disables communication with the authorization server.
		# The requests' Authorization headers are ignored and AuthService provides mock authorization with mock user info.
		# You can provide custom user info by specifying the path pointing to your JSON file.
		"mock_user_info_path": "./mock-userinfo.json",

		# URL of the authorization server's JWK public keys, used for ID token verification.
		# This option is ignored in mock mode or when authorization is disabled.
		"public_keys_url": "http://localhost:3081/.well-known/jwks.json",
	}


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Initialize web container
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		from asab.api import ApiService
		self.ApiService = ApiService(self)
		self.ApiService.initialize_web(self.WebContainer)

		# Initialize authorization
		self.AuthService = asab.web.auth.AuthService(self)
		self.AuthService.install(self.WebContainer)

		# Add routes
		self.WebContainer.WebApp.router.add_get("/noauth", self.noauth)
		self.WebContainer.WebApp.router.add_get("/authn", self.authn)
		self.WebContainer.WebApp.router.add_get("/authz", self.authz)


	@asab.web.auth.noauth
	async def noauth(self, request):
		"""
		NO AUTH
		- no authentication or authorization required
		- `tenant`, `user_info`, `resources` params not allowed
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": "NOT AVAILABLE",
			"user_info": "NOT AVAILABLE",
		}
		return asab.web.rest.json_response(request, data)


	async def authn(
		self,
		request,
		*,
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset],
	):
		"""
		AUTHENTICATION REQUIRED
		- request must be authenticated
		- if there is a tenant ID in the X-Tenant header, the request must be authorized to access that tenant
		- returns 401 if authentication not successful
		"""
		tenant = asab.web.auth.Tenant.get()
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.auth.require("web-auth:access")
	async def authz(
		self,
		request,
		*,
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset]
	):
		"""
		AUTHORIZATION REQUIRED
		- this endpoint is a protected resource
		- request must be authenticated and authorized to access this resource
		- if there is a tenant ID in the X-Tenant header, the request must be authorized to access the resource within that tenant
		- returns 401 if authentication not successful
		- returns 403 if authorization not successful
		"""
		tenant = asab.web.auth.Tenant.get()
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
