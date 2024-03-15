#!/usr/bin/env python3
import asab.web.rest
import asab.web.auth
import typing

# Set up a web container listening at port 8080
asab.Config["web"] = {"listen": "8080"}

# Disables or enables all authentication and authorization, or switches it into MOCK mode.
# When disabled, the `resources` and `userinfo` handler arguments are set to `None`.
asab.Config["auth"]["enabled"] = "mock"  # Mock authorization, useful for debugging.
# asab.Config["auth"]["enabled"] = "yes"   # Authorization is enabled.
# asab.Config["auth"]["enabled"] = "no"    # Authorization is disabled.

# Activating the mock mode disables communication with the authorization server.
# The requests' Authorization headers are ignored and AuthService provides mock authorization with mock user info.
# You can provide custom user info by specifying the path pointing to your JSON file.
asab.Config["auth"]["mock_user_info_path"] = "./mock-userinfo.json"

# URL of the authorization server's JWK public keys, used for ID token verification.
# This option is ignored in mock mode or when authorization is disabled.
asab.Config["auth"]["public_keys_url"] = "http://localhost:3081/.well-known/jwks.json"


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
		self.WebContainer.WebApp.router.add_get("/no_auth", self.no_auth)
		self.WebContainer.WebApp.router.add_get("/auth", self.auth)
		self.WebContainer.WebApp.router.add_get("/auth/resource_check", self.auth_resource)
		self.WebContainer.WebApp.router.add_put("/auth/resource_check", self.auth_resource_put)
		self.WebContainer.WebApp.router.add_get("/{tenant}/required_tenant", self.tenant_in_path)
		self.WebContainer.WebApp.router.add_get("/{tenant}/required_tenant/resource_check", self.tenant_in_path_resources)
		self.WebContainer.WebApp.router.add_get("/configurable_tenant", self.tenant_in_query)
		self.WebContainer.WebApp.router.add_get("/configurable_tenant/resource_check", self.tenant_in_query_resources)


	@asab.web.auth.noauth
	async def no_auth(self, request):
		"""
		NO AUTH
		- authentication skipped

		- `tenant`, `user_info`, `resources` params not allowed
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": "NOT AVAILABLE",
			"user_info": "NOT AVAILABLE",
		}
		return asab.web.rest.json_response(request, data)


	async def auth(self, request, *, user_info: typing.Optional[dict], resources: typing.Optional[frozenset]):
		"""
		TENANT-AGNOSTIC
		- returns 401 if authentication not successful

		- `user_info`, `resources` params allowed
		- `tenant` param not allowed
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.auth.require("something:access", "something:edit")
	async def auth_resource(self, request, *, user_info: typing.Optional[dict], resources: typing.Optional[frozenset]):
		"""
		TENANT-AGNOSTIC + RESOURCE CHECK
		- returns 401 if authentication not successful
		- globally granted resources checked
		- returns 403 if resource access not granted

		- `user_info`, `resources` params allowed
		- `tenant` param not allowed
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.rest.json_schema_handler({
		"type": "object"
	})
	@asab.web.auth.require("something:access", "something:edit")
	async def auth_resource_put(
		self, request, *,
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset],
		json_data: dict
	):
		"""
		Decorator asab.web.auth.require can be used together with other decorators.
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": list(resources) if resources else None,
			"user_info": user_info,
			"json_data": json_data,
		}
		return asab.web.rest.json_response(request, data)


	async def tenant_in_path(
		self, request, *,
		tenant: typing.Optional[str],
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset]
	):
		"""
		TENANT-AWARE
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 403 if tenant not accessible

		- `user_info`, `resources` params allowed
		- `tenant` param required in path, cannot be None
		- `resources` contain tenant-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	async def tenant_in_query(
		self, request, *,
		tenant: typing.Optional[str],
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset]
	):
		"""
		CONFIGURABLY TENANT-AWARE
		- returns 401 if authentication not successful
		- `tenant` expected in query string
		- tenant access checked
		- returns 403 if tenant not accessible
		- `tenant` is set to `None` if `tenant` not in query

		- `user_info`, `resources` params allowed
		- `resources` contain tenant-granted resources if tenant is not None,
			otherwise only globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.auth.require("something:access", "something:edit")
	async def tenant_in_path_resources(
		self, request, *,
		tenant: typing.Optional[str],
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset]
	):
		"""
		TENANT-AWARE + RESOURCE CHECK
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 403 if tenant not accessible
		- tenant-accessible resources checked
		- returns 403 if resource access not granted

		- `user_info`, `resources` params allowed
		- `tenant` param required, cannot be None
		- `resources` contain only resources granted within tenant
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.auth.require("something:access", "something:edit")
	async def tenant_in_query_resources(
		self, request, *,
		tenant: typing.Optional[str],
		user_info: typing.Optional[dict],
		resources: typing.Optional[frozenset]
	):
		"""
		CONFIGURABLY TENANT-AWARE + RESOURCE CHECK
		- returns 401 if authentication not successful
		- `tenant` expected in query string
		- tenant access checked
		- returns 403 if tenant not accessible
		- returns 403 if resource access not granted within tenant
		- `tenant` is set to `None` if `tenant` not in query
		- returns 403 if tenant is None resource access is not granted globally

		- `user_info`, `resources` params allowed
		- `resources` contain tenant-granted resources if tenant is not None,
			otherwise only globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources) if resources else None,
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
