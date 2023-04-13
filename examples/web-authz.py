#!/usr/bin/env python3
import asab.web.rest
import asab.web.authz
import typing

asab.Config.add_defaults({
	"web": {
		"authorization": True,
		# Whether tenant is required in query params
		"tenant": True,
	}
})



class MyApplication(asab.Application):
	"""
	7 possible variants:
	- no tenant, no auth
	- no tenant, authentication
	- no tenant, authentication, resource authorization
	- tenant in path, authentication, tenant authorization
	- tenant in path, authentication, tenant authorization, resource authorization
	- tenant in query, authentication, tenant authorization
	- tenant in query, authentication, tenant authorization, resource authorization
	"""

	def __init__(self):
		super().__init__()

		self.add_module(asab.web.Module)

		# Locate the web service
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")


		self.AuthzService = asab.web.authz.AuthzService(self)
		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
		self.AuthzService.install(self.WebContainer)

		# Add a route to the handler method
		self.WebContainer.WebApp.router.add_get("/no_auth", self.simple)
		self.WebContainer.WebApp.router.add_get("/auth", self.auth)
		self.WebContainer.WebApp.router.add_get("/auth/resource_check", self.auth_resource)
		self.WebContainer.WebApp.router.add_get("/{tenant}/obligatory_tenant", self.tenant_in_path)
		self.WebContainer.WebApp.router.add_get("/{tenant}/obligatory_tenant/resource_check", self.tenant_in_path_resources)
		self.WebContainer.WebApp.router.add_get("/optional_tenant", self.tenant_in_query)
		self.WebContainer.WebApp.router.add_get("/optional_tenant/resource_check", self.tenant_in_query_resources)


	@asab.web.authz.no_auth
	async def simple(self, request):
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


	# async def auth(self, request):  # MINIMAL
	async def auth(self, request, *, user_info: dict, resources: frozenset):
		"""
		TENANT-AGNOSTIC
		- returns 401 if authentication not successful

		- `user_info`, `resources` params allowed
		- `tenant` param not allowed
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth_resource(self, request):  # MINIMAL
	async def auth_resource(self, request, *, user_info: dict, resources: frozenset):
		"""
		TENANT-AGNOSTIC + RESOURCE CHECK
		- returns 401 if authentication not successful
		- globally granted resources checked
		- returns 403 if resources not granted

		- `user_info`, `resources` params allowed
		- `tenant` param not allowed
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": "NOT AVAILABLE",
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_path(self, request, *, tenant: str, user_info: dict, resources: frozenset):
		"""
		TENANT-AWARE
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 401 if tenant not accessible

		- `user_info`, `resources` params allowed
		- `tenant` param required in path, cannot be None
		- `resources` contain tenant-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_query(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		CONFIGURABLY TENANT-AWARE
		- returns 401 if authentication not successful
		- if multitenancy is enabled
			- `tenant` required in query string
			- tenant access checked
			- returns 400 if `tenant` not in query
			- returns 401 if tenant not accessible
		- if multitenancy is disabled
			- `tenant` is set to `None`

		- `user_info`, `resources` params allowed
		- `tenant` param required in query only if multitenancy is enabled
		- `resources` contain tenant-granted resources if multitenancy is enabled,
			otherwise only globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_path_resources(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		TENANT-AWARE + RESOURCE CHECK
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 401 if tenant not accessible
		- tenant-accessible resources checked
		- returns 403 if resources not granted

		- `user_info`, `resources` params allowed
		- `tenant` param required, cannot be None
		- `resources` contain only resources granted within tenant
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_query_resources(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		CONFIGURABLY TENANT-AWARE + RESOURCE CHECK
		- returns 401 if authentication not successful
		- if multitenancy is enabled
			- `tenant` required in query string
			- tenant access checked
			- returns 400 if `tenant` not in query
			- returns 401 if tenant not accessible
			- returns 403 if resources not granted within tenant
		- if multitenancy is disabled
			- `tenant` is set to `None`
			- returns 403 if resources not granted globally

		- `user_info`, `resources` params allowed
		- `tenant` param required only if multitenancy is enabled
		- `resources` contain tenant-granted resources if multitenancy is enabled,
			otherwise only globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
